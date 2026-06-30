#!/bin/bash
cd /Users/zhouzihui/Desktop/cc/employer_sentiment_mvp
python3 -m uvicorn app.main:app --reload --host 0.0.0.0