package org.example.http;

import org.example.config.EntsoEClientConfiguration;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.junit.jupiter.MockitoExtension;

import java.time.Duration;
import java.util.Map;

import static org.assertj.core.api.Assertions.*;

@ExtendWith(MockitoExtension.class)
class DefaultHttpClientTest {

    private EntsoEClientConfiguration config;
    private DefaultHttpClient httpClient;

    @BeforeEach
    void setUp() {
        config = EntsoEClientConfiguration.builder()
                .apiToken("test-token")
                .connectionTimeout(Duration.ofSeconds(5))
                .readTimeout(Duration.ofSeconds(10))
                .maxRetries(2)
                .retryDelay(Duration.ofMillis(100))
                .build();
        httpClient = new DefaultHttpClient(config);
    }

    @Test
    void constructor_ShouldInitializeWithConfiguration() {
        // When & Then
        assertThatCode(() -> new DefaultHttpClient(config))
                .doesNotThrowAnyException();
    }

    @Test
    void buildUrl_WithNoParameters_ShouldReturnBaseUrl() {
        // This would test the private buildUrl method
        // In practice, you'd either make it package-private or test through public methods

        // For now, we test through the public get method with a mock server
        // or use reflection if absolutely necessary for unit testing private methods
    }

    @Test
    void get_WithInvalidUrl_ShouldThrowException() {
        // Given
        String invalidUrl = "not-a-valid-url";
        Map<String, String> params = Map.of("test", "value");

        // When & Then
        assertThatThrownBy(() -> httpClient.get(invalidUrl, params))
                .isInstanceOf(HttpClientException.class)
                .hasMessageContaining("Invalid URL");
    }

    @Test
    void close_ShouldNotThrowException() {
        // When & Then
        assertThatCode(() -> httpClient.close())
                .doesNotThrowAnyException();
    }
}
