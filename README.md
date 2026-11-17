This application is for users to upload a movie csv and get back a cleaned version quickly that is easy to understand. To upload a csv, the user would have to go into /docs put the csv in Post/upload. and There are many modules that support this process. In MP3 we specifically incoperated cache to speed up the process of answering queries by saving it so it does not have to hit the database everytime. You are able to catch work for 90 seconds and it will give you a response of either a Hit or a Miss.SQL is stored in SQLite so even when the server restarts the information is still there. Processing occurs through post/movies/process and this will help clean the movies by doing things like checking for outliers and dupplicates. The commands to start the API and run tests are:

# python -m uvicorn main:app --reload 
# python -m pytest tests -v

One example of a processing request is if you changed the json to {
  "validation": {
    "required_columns": [
      "title", "release_year", "rating", "genre"
    ],
    "numeric_columns": [
      "release_year", "rating"
    ]
  },
  "processing": {
    "remove_duplicates": true,
    "missing": {
      "enabled": true,
      "axis": "rows"
    },
    "outliers": {
      "enabled": true,
      "columns": [
        "rating"
      ],
      "method": "iqr",
      "threshold": 1.5
    }
  }
}

you would then get 

{
  "validation_rows_removed": 0,
  "cleaning_report": {
    "rows_before": 20,
    "rows_after": 16,
    "rows_removed": 4,
    "columns_before": 4,
    "columns_after": 4,
    "columns_removed": 0
  }
}