package org.example.client;

import org.example.config.EntsoEClientConfiguration;
import org.example.http.HttpClient;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.time.Duration;

import static org.assertj.core.api.Assertions.*;

@ExtendWith(MockitoExtension.class)
class EntsoEClientFactoryTest {

    @Mock
    private HttpClient mockHttpClient;

    @Test
    void createClient_WithApiToken_ShouldReturnValidClient() {
        // Given
        String apiToken = "test-api-token";

        // When
        EntsoEClient client = EntsoEClientFactory.createClient(apiToken);

        // Then
        assertThat(client).isNotNull().isInstanceOf(DefaultEntsoEClient.class);
        client.close();
    }

    @Test
    void createClient_WithConfiguration_ShouldReturnValidClient() {
        // Given
        EntsoEClientConfiguration config = EntsoEClientConfiguration.builder()
                .apiToken("test-token")
                .baseUrl("https://test.example.com")
                .connectionTimeout(Duration.ofSeconds(10))
                .build();

        // When
        EntsoEClient client = EntsoEClientFactory.createClient(config);

        // Then
        assertThat(client).isNotNull().isInstanceOf(DefaultEntsoEClient.class);
        client.close();
    }

    @Test
    void createClient_WithConfigurationAndCustomHttpClient_ShouldReturnValidClient() {
        // Given
        EntsoEClientConfiguration config = EntsoEClientConfiguration.builder()
                .apiToken("test-token")
                .baseUrl("https://test.example.com")
                .build();

        // When
        EntsoEClient client = EntsoEClientFactory.createClient(config, mockHttpClient);

        // Then
        assertThat(client).isNotNull().isInstanceOf(DefaultEntsoEClient.class);
        client.close();
    }

    @Test
    void createClient_WithNullApiToken_ShouldThrowException() {
        // When & Then
        assertThatThrownBy(() -> EntsoEClientFactory.createClient((String) null))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("API token cannot be null or empty");
    }

    @Test
    void createClient_WithEmptyApiToken_ShouldThrowException() {
        // When & Then
        assertThatThrownBy(() -> EntsoEClientFactory.createClient(""))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("API token cannot be null or empty");
    }

    @Test
    void createClient_WithBlankApiToken_ShouldThrowException() {
        // When & Then
        assertThatThrownBy(() -> EntsoEClientFactory.createClient("   "))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("API token cannot be null or empty");
    }

    @Test
    void createClient_WithNullConfiguration_ShouldThrowException() {
        // When & Then
        assertThatThrownBy(() -> EntsoEClientFactory.createClient((EntsoEClientConfiguration) null))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("Configuration cannot be null");
    }

    @Test
    void createClient_WithConfigurationHavingNullBaseUrl_ShouldThrowException() {
        // Given
        EntsoEClientConfiguration config = EntsoEClientConfiguration.builder()
                .apiToken("test-token")
                .baseUrl(null)
                .build();

        // When & Then
        assertThatThrownBy(() -> EntsoEClientFactory.createClient(config))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("Base URL cannot be null or empty");
    }
}
