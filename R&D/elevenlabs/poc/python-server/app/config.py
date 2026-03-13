from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    port: int = Field(3000, alias="PORT")
    public_base_url: str | None = Field(default=None, alias="PUBLIC_BASE_URL")
    twilio_stream_url: str | None = Field(default=None, alias="TWILIO_STREAM_URL")
    elevenlabs_api_key: str = Field(alias="ELEVENLABS_API_KEY")
    elevenlabs_agent_id: str = Field(alias="ELEVENLABS_AGENT_ID")
    elevenlabs_realtime_url: str = Field("wss://api.elevenlabs.io/v1/convai/ws", alias="ELEVENLABS_REALTIME_URL")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

    @property
    def resolved_twilio_stream_url(self) -> str:
        if self.twilio_stream_url:
            return self.twilio_stream_url

        if not self.public_base_url:
            raise ValueError("Set TWILIO_STREAM_URL or PUBLIC_BASE_URL to build stream endpoint.")

        normalized = self.public_base_url.rstrip("/")
        if normalized.startswith("http://"):
            normalized = "ws://" + normalized[len("http://") :]
        elif normalized.startswith("https://"):
            normalized = "wss://" + normalized[len("https://") :]

        return f"{normalized}/twilio-media-stream"


settings = Settings()

