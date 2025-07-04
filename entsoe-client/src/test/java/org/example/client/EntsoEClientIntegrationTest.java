package org.example.client;

import org.assertj.core.api.InstanceOfAssertFactories;
import org.example.http.HttpClientException;
import org.example.model.common.AreaCode;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.condition.EnabledIfEnvironmentVariable;

import java.time.LocalDateTime;

import static org.assertj.core.api.Assertions.*;


class EntsoEClientIntegrationTest {

    @Test
    void getActualTotalLoad_WithInvalidAPIKey_ShouldThrow401() throws Exception {
        // Given
        String invalidApiToken = "DUMMY_API_KEY";

        try (EntsoEClient client = EntsoEClientFactory.createClient(invalidApiToken)) {
            LocalDateTime start = LocalDateTime.now().minusDays(2);
            LocalDateTime end = LocalDateTime.now().minusDays(1);

            // When & Then
            assertThatThrownBy(() ->
                    client.getActualTotalLoad(AreaCode.GERMANY, start, end, null)
            )
                    .isInstanceOf(EntsoEClientException.class)
                    .hasMessageContaining("Failed to fetch load data")
                    .hasCauseInstanceOf(HttpClientException.class)
                    .extracting(ex -> ex.getCause())
                    .asInstanceOf(InstanceOfAssertFactories.type(HttpClientException.class))
                    .satisfies(httpEx -> {
                        assertThat(httpEx.getMessage()).contains("Request failed with status 401");
                         assertThat(httpEx.getStatusCode()).isEqualTo(401);
                    });
        }
    }
}
