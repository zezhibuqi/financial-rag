"""Vercel Serverless 入口 —— 导入 Flask app 并暴露为 module-level `app`"""
import os, sys

# 将 backend 目录加入 Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app import app  # noqa: E402
