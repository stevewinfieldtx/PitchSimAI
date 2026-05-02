from fastapi import APIRouter
from services.channel_sim import ChannelMotionRequest, run_channel_sim

router = APIRouter()

@router.post("/analyze")
async def analyze_channel(req: ChannelMotionRequest):
    return await run_channel_sim(req)
