package org.example.client;

import org.example.config.EntsoEClientConfiguration;
import org.example.http.DefaultHttpClient;
import org.example.http.HttpClient;

public class EntsoEClientFactory {

    public static EntsoEClient createClient(String apiToken) {
        if (apiToken == null || apiToken.trim().isEmpty()) {
            throw new IllegalArgumentException("API token cannot be null or empty");
        }

        EntsoEClientConfiguration config = EntsoEClientConfiguration.defaultConfig(apiToken);
        return createClient(config);
    }

    public static EntsoEClient createClient(EntsoEClientConfiguration config) {
        if (config == null) {
            throw new IllegalArgumentException("Configuration cannot be null");
        }

        // Validate configuration properties
        if (config.getBaseUrl() == null || config.getBaseUrl().trim().isEmpty()) {
            throw new IllegalArgumentException("Base URL cannot be null or empty");
        }

        HttpClient httpClient = new DefaultHttpClient(config);
        return new DefaultEntsoEClient(httpClient, config.getBaseUrl());
    }

    public static EntsoEClient createClient(EntsoEClientConfiguration config, HttpClient customHttpClient) {
        if (config == null) {
            throw new IllegalArgumentException("Configuration cannot be null");
        }

        if (config.getBaseUrl() == null || config.getBaseUrl().trim().isEmpty()) {
            throw new IllegalArgumentException("Base URL cannot be null or empty");
        }

        return new DefaultEntsoEClient(customHttpClient, config.getBaseUrl());
    }
}
