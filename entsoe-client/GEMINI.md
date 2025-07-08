### Project Overview

This is a Java 21 project built with Gradle. It implements a client for the ENTSO-E (European Network of Transmission System Operators for Electricity) API. The project emphasizes clean architecture, modern Java practices, and robust testing.

### Core Principles

- **Dependency Injection (DI):** The application should be designed with DI in mind. Use constructor injection to provide dependencies. Frameworks like Guice or Spring are not currently used; DI is managed manually.
- **Immutability:** Prefer immutable objects and classes where possible, especially for data transfer objects (DTOs) and model entities.
- **Clean Code:** Code should be clean, readable, and well-documented. Follow standard Java naming conventions.
- **Code Style & Formatting:** The project uses Spotless for code formatting. All code should be formatted before committing. The style is likely configured in `build.gradle.kts`.

### Key Directories

- `src/main/java`: Contains the main application source code.
- `src/main/groovy`: Contains Groovy source code, possibly for scripts or utility classes.
- `src/test/java`: Contains Java unit and integration tests.
- `src/test/groovy`: Contains Groovy tests (likely using Spock).
- `build.gradle.kts`: The Gradle build script, defining dependencies, plugins, and tasks.

### Development Workflow

1.  **Building the Project:**
    ```bash
    ./gradlew build
    ```

2.  **Running Tests:**
    All new features and bug fixes must be accompanied by appropriate tests.
    ```bash
    ./gradlew test
    ```

3.  **Checking Code Style:**
    Before committing, ensure code conforms to the project's style guidelines by running Spotless.
    ```bash
    ./gradlew spotlessCheck
    ```

4.  **Applying Code Style:**
    To automatically fix formatting issues, run:
    ```bash
    ./gradlew spotlessApply
    ```
