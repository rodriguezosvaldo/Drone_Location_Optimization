"""Launch the MetroSafe web interface."""

import os

import uvicorn

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    # Render sets RENDER=true; disable reload and bind publicly there.
    on_render = os.environ.get("RENDER", "").lower() == "true"

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0" if on_render else "127.0.0.1",
        port=port,
        reload=not on_render,
        app_dir="backend",
    )
