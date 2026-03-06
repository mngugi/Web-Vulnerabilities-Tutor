#!/bin/bash
# Must be run from project root (where app/ and data/ exist)
export FLASK_APP=app.main
export FLASK_ENV=development
flask run