
import io
import json
import logging
from pathlib import Path
import pandas as pd
from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from src import DatasetInfo, HealthResponse,  ProcessConfig, ProcessingReport,setup_logging
from data_pipeline import create_cleaning_report, process_data, validate_dataframe 

from src.middleware import log_requests

setup_logging(verbose=True)
logger = logging.getLogger(__name__)

from src import (MovieStorage,MovieUploadInfo,MovieDataResponse, MovieProcessingReport,MovieCache)
from src.storage import MOVIE_COLUMNS
cache = MovieCache()

app = FastAPI(title="Data Processing API", version="1.0.0")
storage = MovieStorage()
app.middleware("http")(log_requests)

@app.get("/health", response_model=HealthResponse)
def health_check():
    """Return the application status and version."""
    return{"status": "ok", "version": "1.0.0"}

@app.post("/upload", response_model=MovieUploadInfo)
async def upload_movies(file: UploadFile = File(...)):
    """Read and store a CSV upload."""
    suffix = Path(file.filename or "").suffix.lower()
    if suffix != ".csv":
        logger.warning(f"Unsupported file format: {suffix}")
        raise HTTPException(status_code=400, detail="Only CSV files are supported")

    contents = await file.read()
    try:
        df = pd.read_csv(io.BytesIO(contents))
    except (pd.errors.EmptyDataError, pd.errors.ParserError, UnicodeDecodeError) as error:
        logger.warning(f"Cannot read CSV: {error}")
        raise HTTPException(status_code=400, detail="Cannot read the uploaded CSV")
# validation and reorder 
    if sorted(df.columns) != sorted(MOVIE_COLUMNS):
        raise HTTPException(status_code=400, detail="wrong columns")
    if df.empty:
        raise HTTPException(status_code=400, detail = "no data rows")
    df = df[MOVIE_COLUMNS]
    storage.save(df)
    cache.invalidate()
    logger.info(f"Uploaded movies filename={file.filename}, rows={len(df)}")
    return {"filename": file.filename,
        "rows": len(df),
        "columns": len(df.columns),
        "column_names": list(df.columns),
    }


@app.get("/movies",response_model=MovieDataResponse)
def get_movies(limit: int = Query(default=100, ge=1)):
    """Return up to limit stored movies."""
    cached = cache.get(limit)
    if cached is not None:
        logger.info(f"Returned movies from catche")
        return cached
    total_rows = storage.count_movies()
    if total_rows == 0:
        records =[]
    else:
        records = storage.select_columns(MOVIE_COLUMNS, limit)
    response = {"data": records,"total_rows":total_rows}
    cache.set(limit, response)
    logger.info(f"Returned {len(records)} movies")
    return response


@app.get("/movies/search", response_model=list[dict])
def query_movies(
    columns: list[str] = Query(default=["title"]),
    min_rating: float = Query(default=0, ge=0, le=10),
    limit: int = Query(default=100, ge=1)
):
    try:
        movies = storage.query_movies(columns, min_rating, limit)
    except ValueError as error:
        logger.warning(f"Invalid call: {error}")
        raise HTTPException(status_code=400)
    logger.info(f"Queried movies: rows={len(movies)}, columns={columns}")
    return movies
# TODO: Call storage.query_movies(columns, min_rating, limit).
# Catch ValueError and raise HTTPException with status 400.
# Return id plus the selected fields, or [] if there are no matches.
# Log the selected columns and returned row count at INFO.


@app.post(
"/movies/process", response_model=MovieProcessingReport)
def process_movies(config: ProcessConfig):
    """Validate and process a stored dataset using MP1 functions."""

    df = storage.get()
    if df.empty:
        logger.warning(f"No movies found")
        raise HTTPException(status_code=400
        , detail="dataset not found")
    
    config_dict = config.model_dump()
    required_columns = config_dict["validation"]["required_columns"]
    numeric_columns = config_dict["validation"]["numeric_columns"]

    for col in numeric_columns:
        if col not in df.columns: 
            logger.warning(f"Numeric column not found: {col}")
            raise HTTPException(status_code=400, detail=f"Numeric column not found: {col}")
    try:
        validated = validate_dataframe(df, required_columns, numeric_columns)
        validation_rows_removed = len(df) - len(validated)
        validated_copy = validated.copy()
        processed = process_data(validated, config_dict)


        cleaning_report = create_cleaning_report(validated_copy, processed)
    except ValueError as error:
        logger.warning(f"failed:{error}")
        raise HTTPException(status_code=400, detail=str(error))
    storage.save(processed)
    cache.invalidate()
    logger.info(f"Processed  movies: validation_removed={validation_rows_removed}")
    return{
        "validation_rows_removed": validation_rows_removed,
        "cleaning_report": cleaning_report,
    }

#python -m uvicorn main:app --reload
#http://127.0.0.1:8000/docs

#restart control+C