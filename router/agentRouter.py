from fastapi import APIRouter, HTTPException, Form
import sys
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
from util import getApiKey, ControlMongo

agentRoute = APIRouter()

