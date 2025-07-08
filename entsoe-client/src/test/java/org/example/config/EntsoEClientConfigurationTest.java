package org.example.config;

import static org.assertj.core.api.Assertions.*;

import java.time.Duration;
import java.util.Map;
import org.junit.jupiter.api.Test;

class EntsoEClientConfigurationTest {

  @Test
  void builder_WithRequiredFields_ShouldCreateConfiguration() {
    // Given
    String apiToken = "test-token";

    // When
    EntsoEClientConfiguration config =
        EntsoEClientConfiguration.builder().apiToken(apiToken).build();

    // Then
    assertThat(config.getApiToken()).isEqualTo(apiToken);
    assertThat(config.getBaseUrl()).isEqualTo("https://web-api.tp.entsoe.eu/api");
    assertThat(config.getConnectionTimeout()).isEqualTo(Duration.ofSeconds(30));
    assertThat(config.getReadTimeout()).isEqualTo(Duration.ofSeconds(60));
    assertThat(config.getMaxRetries()).isEqualTo(3);
    assertThat(config.getRetryDelay()).isEqualTo(Duration.ofSeconds(1));
    assertThat(config.isEnableLogging()).isTrue();
  }

  @Test
  void builder_WithAllFields_ShouldCreateConfiguration() {
    // Given
    String apiToken = "test-token";
    String baseUrl = "https://custom.api.com";
    Duration connectionTimeout = Duration.ofSeconds(45);
    Duration readTimeout = Duration.ofSeconds(90);
    int maxRetries = 5;
    Duration retryDelay = Duration.ofSeconds(2);
    Map<String, String> customHeaders = Map.of("X-Custom", "value");

    // When
    EntsoEClientConfiguration config =
        EntsoEClientConfiguration.builder()
            .apiToken(apiToken)
            .baseUrl(baseUrl)
            .connectionTimeout(connectionTimeout)
            .readTimeout(readTimeout)
            .maxRetries(maxRetries)
            .retryDelay(retryDelay)
            .enableLogging(false)
            .customHeaders(customHeaders)
            .build();

    // Then
    assertThat(config.getApiToken()).isEqualTo(apiToken);
    assertThat(config.getBaseUrl()).isEqualTo(baseUrl);
    assertThat(config.getConnectionTimeout()).isEqualTo(connectionTimeout);
    assertThat(config.getReadTimeout()).isEqualTo(readTimeout);
    assertThat(config.getMaxRetries()).isEqualTo(maxRetries);
    assertThat(config.getRetryDelay()).isEqualTo(retryDelay);
    assertThat(config.isEnableLogging()).isFalse();
    assertThat(config.getCustomHeaders()).isEqualTo(customHeaders);
  }

  @Test
  void defaultConfig_ShouldCreateConfigurationWithDefaults() {
    // Given
    String apiToken = "test-token";

    // When
    EntsoEClientConfiguration config = EntsoEClientConfiguration.defaultConfig(apiToken);

    // Then
    assertThat(config.getApiToken()).isEqualTo(apiToken);
    assertThat(config.getBaseUrl()).isEqualTo("https://web-api.tp.entsoe.eu/api");
    assertThat(config.getConnectionTimeout()).isEqualTo(Duration.ofSeconds(30));
  }

  @Test
  void builder_WithoutApiToken_ShouldThrowException() {
    // When & Then
    assertThatThrownBy(() -> EntsoEClientConfiguration.builder().build())
        .isInstanceOf(NullPointerException.class);
  }
}
