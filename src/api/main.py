"""FastAPI app for Asian Food Intelligence Explorer."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from loguru import logger

from src.config import get_settings
from src.models.recommendation import RecommendationRequest
from src.services.dish_repository import DishRepository
from src.services.embedding_service import EmbeddingService
from src.services.similarity_engine import SimilarityEngine
from src.services.recommendation_engine import RecommendationEngine
from src.models.user import UserProfile, UserPreference
from src.api.errors import NotFoundError, ServiceUnavailableError


repository: DishRepository | None = None
embedding_service: EmbeddingService | None = None
similarity_engine: SimilarityEngine | None = None
recommendation_engine: RecommendationEngine | None = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """Initialize services on startup."""
    global repository, embedding_service, similarity_engine, recommendation_engine

    settings = get_settings()
    logger.info(f"Starting {settings.app_name} v{settings.version}...")

    try:
        repository = DishRepository(settings.data_dir)
        repository.load()
        logger.info(f"Loaded {repository.count()} dishes")

        embedding_service = EmbeddingService(repository)
        embedding_service.compute_all_embeddings()

        similarity_engine = SimilarityEngine(repository, embedding_service)

        recommendation_engine = RecommendationEngine(
            repository, embedding_service, similarity_engine
        )
        recommendation_engine.initialize_bm25()

        logger.info("All services initialized")
    except Exception as e:
        logger.error(f"Failed to initialize: {e}")
        raise

    yield
    logger.info("Shutting down")


settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    description="Asian cuisine recommendation system",
    version=settings.version,
    lifespan=lifespan,
)

# Enable CORS
cors_origins = settings.cors_origins.split(",") if settings.cors_origins else ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request, exc):
    logger.error(f"HTTP Error: {exc.status_code} - {exc.detail}")
    return {"success": False, "error": f"ERR_{exc.status_code}", "message": str(exc.detail)}


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    return {"success": False, "error": "VALIDATION_ERROR", "message": str(exc.errors())}


@app.exception_handler(Exception)
async def generic_exception_handler(request, exc):
    logger.exception(f"Unhandled error: {exc}")
    return {"success": False, "error": "INTERNAL_ERROR", "message": "An unexpected error occurred"}


@app.get("/")
async def root():
    return {
        "status": "ok",
        "service": settings.app_name,
        "version": settings.version,
        "dishes_loaded": repository.count() if repository else 0,
    }


@app.get("/health")
async def health():
    """Health check for containers."""
    if repository is None:
        return {"status": "unhealthy", "reason": "not initialized"}
    return {"status": "healthy", "dishes": repository.count()}


@app.get("/api/v1/dishes")
async def list_dishes(
    cuisine: str | None = Query(None),
    vegetarian: bool = Query(False),
):
    """List dishes with optional filtering."""
    if repository is None:
        raise ServiceUnavailableError("DishRepository")

    if cuisine:
        dishes = repository.get_by_cuisine(cuisine)
    elif vegetarian:
        dishes = [d for d in repository.get_all() if d.is_vegetarian]
    else:
        dishes = repository.get_all()

    return {"count": len(dishes), "dishes": [d.model_dump() for d in dishes]}


@app.get("/api/v1/dishes/{dish_id}")
async def get_dish(dish_id: str):
    if repository is None:
        raise ServiceUnavailableError("DishRepository")
    dish = repository.get_by_id(dish_id)
    if not dish:
        raise NotFoundError("Dish", dish_id)
    return dish.model_dump()


@app.get("/api/v1/cuisines")
async def list_cuisines():
    if repository is None:
        raise ServiceUnavailableError("DishRepository")
    return {"cuisines": repository.get_available_cuisines()}


@app.get("/api/v1/taste-map")
async def get_taste_map(cuisine: str | None = Query(None)):
    if repository is None:
        raise ServiceUnavailableError("DishRepository")

    dishes = repository.get_all()
    if cuisine:
        dishes = [d for d in dishes if d.cuisine.lower() == cuisine.lower()]

    taste_map_data = [
        {
            "dish_id": d.id,
            "name": d.name,
            "cuisine": d.cuisine,
            "x": d.taste_profile.to_taste_map_coords()[0],
            "y": d.taste_profile.to_taste_map_coords()[1],
            "spice_level": d.taste_profile.spice_level,
            "richness": d.taste_profile.richness,
            "image_color": d.image_color,
        }
        for d in dishes
    ]
    return {"dishes": taste_map_data}


@app.get("/api/v1/similar/{dish_id}")
async def get_similar_dishes(
    dish_id: str,
    limit: int = Query(10, ge=1, le=20),
    method: str = Query("hybrid"),
):
    if repository is None:
        raise ServiceUnavailableError("DishRepository")
    if not repository.get_by_id(dish_id):
        raise NotFoundError("Dish", dish_id)
    if similarity_engine is None:
        raise ServiceUnavailableError("SimilarityEngine")

    similar = similarity_engine.find_similar_dishes(dish_id, top_k=limit, method=method)
    return {
        "source_dish": dish_id,
        "method": method,
        "similar_dishes": [{"dish": d.model_dump(), "similarity_score": round(s, 4)} for d, s in similar],
    }


@app.post("/api/v1/recommend")
async def get_recommendations(request: RecommendationRequest):
    if recommendation_engine is None:
        raise ServiceUnavailableError("RecommendationEngine")

    if request.max_results > settings.max_results:
        request.max_results = settings.max_results

    user_profile = None
    if request.user_profile:
        pref_data = request.user_profile.get("preferences", {})
        user_profile = UserProfile(
            preferences=UserPreference(**pref_data) if pref_data else UserPreference()
        )

    response = recommendation_engine.recommend(
        query=request.query,
        user_profile=user_profile,
        similar_to=request.similar_to,
        max_results=request.max_results,
        cuisine_filter=request.cuisine_filter,
        min_spice=request.min_spice,
        max_spice=request.max_spice,
        vegetarian_only=request.vegetarian_only,
        use_hybrid=request.use_hybrid,
    )
    return response.model_dump()


@app.get("/api/v1/search")
async def search_dishes(
    q: str = Query(...),
    limit: int = Query(10, ge=1, le=20),
):
    if recommendation_engine is None:
        raise ServiceUnavailableError("RecommendationEngine")

    response = recommendation_engine.recommend(query=q, max_results=limit, use_hybrid=True)
    return {
        "query": q,
        "results": [{"dish": r.dish.model_dump(), "score": r.score, "reasons": r.match_reasons} for r in response.recommendations],
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.host, port=settings.port, log_level="debug" if settings.debug else "info")
