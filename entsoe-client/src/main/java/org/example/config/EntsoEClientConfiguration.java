package org.example.config;

import java.time.Duration;
import java.util.Map;
import lombok.Builder;
import lombok.Data;
import lombok.NonNull;

@Data
@Builder
public class EntsoEClientConfiguration {

  @NonNull private String apiToken;

  @Builder.Default private String baseUrl = "https://web-api.tp.entsoe.eu/api";

  @Builder.Default private Duration connectionTimeout = Duration.ofSeconds(30);

  @Builder.Default private Duration readTimeout = Duration.ofSeconds(60);

  @Builder.Default private int maxRetries = 3;

  @Builder.Default private Duration retryDelay = Duration.ofSeconds(1);

  @Builder.Default private boolean enableLogging = true;

  private Map<String, String> customHeaders;

  public static EntsoEClientConfiguration defaultConfig(String apiToken) {
    return EntsoEClientConfiguration.builder().apiToken(apiToken).build();
  }
}
