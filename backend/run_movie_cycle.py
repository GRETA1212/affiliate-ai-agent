from app.services.movie_orchestrator import plan_movie_work


if __name__ == "__main__":
    result = plan_movie_work(limit=10)
    print(result.model_dump_json(indent=2))
