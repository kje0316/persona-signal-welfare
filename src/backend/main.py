# FastAPI 애플리케이션 메인 파일
# 서버 실행을 위한 엔트리포인트

from fastapi import FastAPI

app = FastAPI(title="Persona Signal Welfare API")

@app.get("/")
def read_root():
    return {"message": "Welcome to Persona Signal Welfare API"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)