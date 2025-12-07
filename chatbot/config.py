"""
Configuration for Vietnam Football Knowledge Graph Chatbot

Supports small language models (<= 1B parameters):
- Qwen2-0.5B-Instruct (500M params)
- Qwen2-1.5B-Instruct (1.5B params - slightly over but very efficient)
- microsoft/phi-2 (2.7B - backup option)
- TinyLlama/TinyLlama-1.1B-Chat-v1.0 (1.1B params)
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
BASE_DIR = Path(__file__).parent.parent
load_dotenv(BASE_DIR / '.env')

# =============================================================================
# NEO4J SETTINGS
# =============================================================================
NEO4J_URI = os.environ.get("NEO4J_URI", "neo4j+s://localhost:7687")
NEO4J_USER = os.environ.get("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD", "password")

# =============================================================================
# MODEL SETTINGS - Small Language Models (<= 1B params)
# =============================================================================

# Primary model: Qwen2-0.5B (500M params) - Very efficient
MODEL_NAME = os.environ.get("LLM_MODEL", "Qwen/Qwen2-0.5B-Instruct")

# Alternative models (uncomment to use):
# MODEL_NAME = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"  # 1.1B params
# MODEL_NAME = "Qwen/Qwen2-1.5B-Instruct"  # 1.5B params
# MODEL_NAME = "microsoft/phi-2"  # 2.7B params (backup)

# Model inference settings
MODEL_MAX_LENGTH = 2048
MODEL_TEMPERATURE = 0.1
MODEL_TOP_P = 0.9
MODEL_DO_SAMPLE = True

# Device settings
DEVICE = os.environ.get("DEVICE", "cuda")  # "cuda" or "cpu"
TORCH_DTYPE = "float16"  # Use float16 for efficiency

# =============================================================================
# EMBEDDING SETTINGS
# =============================================================================
# Small efficient embedding model
EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
EMBEDDING_DIMENSION = 384

# =============================================================================
# GRAPH RAG SETTINGS
# =============================================================================
# Maximum hops for multi-hop reasoning
MAX_HOPS = 3

# Number of relevant entities to retrieve
TOP_K_ENTITIES = 10

# Number of relevant paths to retrieve
TOP_K_PATHS = 5

# Context window for graph information
MAX_GRAPH_CONTEXT_LENGTH = 1500

# =============================================================================
# EVALUATION SETTINGS
# =============================================================================
# Number of questions to generate
NUM_QUESTIONS_TOTAL = 2500
NUM_QUESTIONS_TRUE_FALSE = 1000
NUM_QUESTIONS_MCQ = 1000
NUM_QUESTIONS_YES_NO = 500

# Evaluation output
EVALUATION_DIR = BASE_DIR / "chatbot" / "evaluation"
QUESTIONS_FILE = EVALUATION_DIR / "questions.json"
RESULTS_FILE = EVALUATION_DIR / "results.json"

# =============================================================================
# PATHS
# =============================================================================
CACHE_DIR = BASE_DIR / "chatbot" / "cache"
MODELS_DIR = BASE_DIR / "chatbot" / "models"

# Create directories
CACHE_DIR.mkdir(parents=True, exist_ok=True)
MODELS_DIR.mkdir(parents=True, exist_ok=True)
EVALUATION_DIR.mkdir(parents=True, exist_ok=True)
