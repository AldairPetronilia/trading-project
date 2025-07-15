from .container import Container


def hello() -> str:
    return "Hello from entsoe-client!"


# Global container instance - single source of truth for the entire application
container = Container()

# Wire the container for dependency injection
container.wire(modules=[__name__])
