from pydantic import AnyUrl, Field, BaseModel, validator
from pathlib import Path
from manifest import Manifest


class Server(BaseModel):
    name: str
    url: AnyUrl

    @validator("url")
    def validate_url(cls, url: AnyUrl) -> str:
        return str(url)


class Configuration(Manifest):
    app_dir: Path = Field(exclude=True)
    config_file: Path | None = Field(exclude=True)

    servers: list[Server] = Field(default=[Server(name="default", url="http://localhost:8080")])
    current_server: str = "default"

    @property
    def full_path(self) -> Path | None:
        if self.config_file is None:
            return None

        return self.app_dir / self.config_file

    def get_server(self, name: str) -> Server | None:
        for server in self.servers:
            if server.name == name:
                return server

        return None
