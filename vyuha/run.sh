#!/bin/bash
# Run both backend and frontend servers

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}Starting VYUHA servers...${NC}"

# Start backend
echo -e "${GREEN}[Backend]${NC} Starting FastAPI on http://127.0.0.1:8000"
(cd backend && source venv/bin/activate && uvicorn main:app --reload --port 8000) &
BACKEND_PID=$!

# Start frontend
echo -e "${GREEN}[Frontend]${NC} Starting Vite on http://localhost:5173"
(cd frontend && npm run dev) &
FRONTEND_PID=$!

echo -e "${GREEN}Both servers running!${NC}"
echo -e "Backend PID: $BACKEND_PID"
echo -e "Frontend PID: $FRONTEND_PID"
echo -e "\nPress Ctrl+C to stop both servers"

# Wait for Ctrl+C
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; echo -e '\n${YELLOW}Servers stopped.${NC}'; exit" INT TERM
wait