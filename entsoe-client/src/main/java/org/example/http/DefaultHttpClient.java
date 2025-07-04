package org.example.http;

import lombok.extern.slf4j.Slf4j;
import org.example.config.EntsoEClientConfiguration;

import java.io.IOException;
import java.net.URI;
import java.net.URISyntaxException;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.util.Map;
import java.util.StringJoiner;

@Slf4j
public class DefaultHttpClient implements HttpClient {

    private final java.net.http.HttpClient httpClient;
    private final EntsoEClientConfiguration config;
    private final RetryHandler retryHandler;

    public DefaultHttpClient(EntsoEClientConfiguration config) {
        this.config = config;
        this.httpClient = java.net.http.HttpClient.newBuilder()
                .connectTimeout(config.getConnectionTimeout())
                .build();
        this.retryHandler = new RetryHandler(config.getMaxRetries(), config.getRetryDelay());
    }

    @Override
    public String get(String url, Map<String, String> parameters) throws HttpClientException {
        String fullUrl = buildUrl(url, parameters);

        try {
            URI uri = new URI(fullUrl);
            if (uri.getScheme() == null) {
                throw new HttpClientException("Invalid URL: " + fullUrl, null);
            }
        } catch (URISyntaxException e) {
            throw new HttpClientException("Invalid URL: " + fullUrl, e);
        }

        return retryHandler.execute(() -> {
            HttpRequest request = buildRequest(fullUrl);

            try {
                HttpResponse<String> response = httpClient.send(request,
                        HttpResponse.BodyHandlers.ofString());

                if (response.statusCode() >= 200 && response.statusCode() < 300) {
                    log.debug("Request successful: {}", response.statusCode());
                    return response.body();
                } else {
                    String errorMsg = String.format("Request failed with status %d", response.statusCode());
                    log.error("HTTP error: {}", errorMsg);
                    throw new HttpClientException(errorMsg, response.statusCode(), response.body());
                }

            } catch (IOException | InterruptedException e) {
                log.error("Request execution failed", e);
                throw new HttpClientException("Request execution failed", e);
            }
        });
    }

    private String buildUrl(String baseUrl, Map<String, String> parameters) {
        if (parameters == null || parameters.isEmpty()) {
            return baseUrl;
        }

        StringJoiner joiner = new StringJoiner("&");
        parameters.forEach((key, value) -> {
            if (value != null) {
                joiner.add(key + "=" + value);
            }
        });

        return baseUrl + "?" + joiner;
    }

    private HttpRequest buildRequest(String url) throws HttpClientException {
        try {
            HttpRequest.Builder builder = HttpRequest.newBuilder()
                    .uri(new URI(url))
                    .timeout(config.getReadTimeout())
                    .GET();

            // Add authentication header
            builder.header("Authorization", "Bearer " + config.getApiToken());

            // Add custom headers if any
            if (config.getCustomHeaders() != null) {
                config.getCustomHeaders().forEach(builder::header);
            }

            return builder.build();

        } catch (URISyntaxException e) {
            throw new HttpClientException("Invalid URL: " + url, e);
        }
    }

    @Override
    public void close() {
        // Java 11 HttpClient doesn't need explicit closing
        log.debug("HTTP client closed");
    }
}
