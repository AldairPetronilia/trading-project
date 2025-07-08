package org.example.client;

import static org.assertj.core.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

import java.time.LocalDateTime;
import java.util.Map;
import javax.xml.bind.JAXBException;
import org.example.http.HttpClient;
import org.example.http.HttpClientException;
import org.example.model.common.AreaCode;
import org.example.model.load.GLMarketDocument;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

/**
 * Unit tests for DefaultEntsoEClient Tests all load domain endpoints and error handling scenarios
 */
@ExtendWith(MockitoExtension.class)
class DefaultEntsoEClientTest {

  @Mock private HttpClient mockHttpClient;

  private DefaultEntsoEClient client;
  private final String baseUrl = "https://test-api.entsoe.eu";

  private final String validXmlResponse =
      """
            <?xml version="1.0" encoding="UTF-8"?>
            <GL_MarketDocument xmlns="urn:iec62325.351:tc57wg16:451-6:generationloaddocument:3:0">
                <mRID>test-mrid-123</mRID>
                <revisionNumber>1</revisionNumber>
            </GL_MarketDocument>
            """;

  @BeforeEach
  void setUp() {
    client = new DefaultEntsoEClient(mockHttpClient, baseUrl);
  }

  @Test
  void getActualTotalLoad_ShouldCallHttpClientWithCorrectParameters() throws Exception {
    // Given
    when(mockHttpClient.get(eq(baseUrl), any())).thenReturn(validXmlResponse);

    LocalDateTime start = LocalDateTime.of(2025, 1, 1, 0, 0);
    LocalDateTime end = LocalDateTime.of(2025, 1, 2, 0, 0);
    AreaCode biddingZone = AreaCode.GERMANY;

    // When
    GLMarketDocument result = client.getActualTotalLoad(biddingZone, start, end, null);

    // Then
    ArgumentCaptor<Map<String, String>> paramsCaptor = ArgumentCaptor.forClass(Map.class);
    verify(mockHttpClient).get(eq(baseUrl), paramsCaptor.capture());

    Map<String, String> params = paramsCaptor.getValue();
    assertThat(params)
        .containsEntry("documentType", "A65")
        .containsEntry("processType", "A16")
        .containsEntry("outBiddingZone_Domain", biddingZone.getCode())
        .containsEntry("periodStart", "202501010000")
        .containsEntry("periodEnd", "202501020000")
        .doesNotContainKey("offset"); // Should not include null offset

    assertThat(result).isNotNull();
    assertThat(result.getMRID()).isEqualTo("test-mrid-123");
  }

  @Test
  void getActualTotalLoad_WithOffset_ShouldIncludeOffsetParameter() throws Exception {
    // Given
    when(mockHttpClient.get(eq(baseUrl), any())).thenReturn(validXmlResponse);

    LocalDateTime start = LocalDateTime.of(2025, 1, 1, 0, 0);
    LocalDateTime end = LocalDateTime.of(2025, 1, 2, 0, 0);
    Integer offset = 100;

    // When
    client.getActualTotalLoad(AreaCode.FRANCE, start, end, offset);

    // Then
    ArgumentCaptor<Map<String, String>> paramsCaptor = ArgumentCaptor.forClass(Map.class);
    verify(mockHttpClient).get(eq(baseUrl), paramsCaptor.capture());

    Map<String, String> params = paramsCaptor.getValue();
    assertThat(params)
        .containsEntry("offset", "100")
        .containsEntry("documentType", "A65")
        .containsEntry("processType", "A16");
  }

  @Test
  void getDayAheadLoadForecast_ShouldUseCorrectProcessType() throws Exception {
    // Given
    when(mockHttpClient.get(eq(baseUrl), any())).thenReturn(validXmlResponse);

    LocalDateTime start = LocalDateTime.of(2025, 1, 1, 0, 0);
    LocalDateTime end = LocalDateTime.of(2025, 1, 2, 0, 0);

    // When
    client.getDayAheadLoadForecast(AreaCode.SPAIN, start, end, null);

    // Then
    ArgumentCaptor<Map<String, String>> paramsCaptor = ArgumentCaptor.forClass(Map.class);
    verify(mockHttpClient).get(eq(baseUrl), paramsCaptor.capture());

    Map<String, String> params = paramsCaptor.getValue();
    assertThat(params)
        .containsEntry("documentType", "A65")
        .containsEntry("processType", "A01") // Day-ahead process type
        .containsEntry("outBiddingZone_Domain", AreaCode.SPAIN.getCode());
  }

  @Test
  void getWeekAheadLoadForecast_ShouldUseCorrectProcessType() throws Exception {
    // Given
    when(mockHttpClient.get(eq(baseUrl), any())).thenReturn(validXmlResponse);

    LocalDateTime start = LocalDateTime.of(2025, 1, 1, 0, 0);
    LocalDateTime end = LocalDateTime.of(2025, 1, 8, 0, 0);

    // When
    client.getWeekAheadLoadForecast(AreaCode.ITALY, start, end, null);

    // Then
    ArgumentCaptor<Map<String, String>> paramsCaptor = ArgumentCaptor.forClass(Map.class);
    verify(mockHttpClient).get(eq(baseUrl), paramsCaptor.capture());

    Map<String, String> params = paramsCaptor.getValue();
    assertThat(params)
        .containsEntry("documentType", "A65")
        .containsEntry("processType", "A31"); // Week-ahead process type
  }

  @Test
  void getMonthAheadLoadForecast_ShouldUseCorrectProcessType() throws Exception {
    // Given
    when(mockHttpClient.get(eq(baseUrl), any())).thenReturn(validXmlResponse);

    LocalDateTime start = LocalDateTime.of(2025, 1, 1, 0, 0);
    LocalDateTime end = LocalDateTime.of(2025, 2, 1, 0, 0);

    // When
    client.getMonthAheadLoadForecast(AreaCode.NETHERLANDS, start, end, 50);

    // Then
    ArgumentCaptor<Map<String, String>> paramsCaptor = ArgumentCaptor.forClass(Map.class);
    verify(mockHttpClient).get(eq(baseUrl), paramsCaptor.capture());

    Map<String, String> params = paramsCaptor.getValue();
    assertThat(params)
        .containsEntry("documentType", "A65")
        .containsEntry("processType", "A32") // Month-ahead process type
        .containsEntry("offset", "50");
  }

  @Test
  void getYearAheadLoadForecast_ShouldUseCorrectProcessType() throws Exception {
    // Given
    when(mockHttpClient.get(eq(baseUrl), any())).thenReturn(validXmlResponse);

    LocalDateTime start = LocalDateTime.of(2025, 1, 1, 0, 0);
    LocalDateTime end = LocalDateTime.of(2026, 1, 1, 0, 0);

    // When
    client.getYearAheadLoadForecast(AreaCode.AUSTRIA, start, end, null);

    // Then
    ArgumentCaptor<Map<String, String>> paramsCaptor = ArgumentCaptor.forClass(Map.class);
    verify(mockHttpClient).get(eq(baseUrl), paramsCaptor.capture());

    Map<String, String> params = paramsCaptor.getValue();
    assertThat(params)
        .containsEntry("documentType", "A65")
        .containsEntry("processType", "A33"); // Year-ahead process type
  }

  @Test
  void getYearAheadForecastMargin_ShouldUseCorrectDocumentAndProcessType() throws Exception {
    // Given
    when(mockHttpClient.get(eq(baseUrl), any())).thenReturn(validXmlResponse);

    LocalDateTime start = LocalDateTime.of(2025, 1, 1, 0, 0);
    LocalDateTime end = LocalDateTime.of(2026, 1, 1, 0, 0);

    // When
    client.getYearAheadForecastMargin(AreaCode.GERMANY, start, end, null);

    // Then
    ArgumentCaptor<Map<String, String>> paramsCaptor = ArgumentCaptor.forClass(Map.class);
    verify(mockHttpClient).get(eq(baseUrl), paramsCaptor.capture());

    Map<String, String> params = paramsCaptor.getValue();
    assertThat(params)
        .containsEntry("documentType", "A70") // Load forecast margin document type
        .containsEntry("processType", "A33"); // Year-ahead process type
  }

  @Test
  void executeRequest_WhenHttpClientThrowsException_ShouldThrowEntsoEClientException()
      throws Exception {
    // Given
    when(mockHttpClient.get(eq(baseUrl), any()))
        .thenThrow(new HttpClientException("Connection failed", 500, "Internal Server Error"));

    // When & Then
    assertThatThrownBy(
            () ->
                client.getActualTotalLoad(
                    AreaCode.GERMANY, LocalDateTime.now().minusDays(1), LocalDateTime.now(), null))
        .isInstanceOf(EntsoEClientException.class)
        .hasMessageContaining("Failed to fetch load data")
        .hasCauseInstanceOf(HttpClientException.class);
  }

  @Test
  void parseXmlResponse_WhenInvalidXml_ShouldThrowEntsoEClientException() throws Exception {
    // Given
    when(mockHttpClient.get(eq(baseUrl), any())).thenReturn("invalid xml");

    // When & Then
    assertThatThrownBy(
            () ->
                client.getActualTotalLoad(
                    AreaCode.BELGIUM, LocalDateTime.now().minusDays(1), LocalDateTime.now(), null))
        .isInstanceOf(EntsoEClientException.class)
        .hasMessageContaining("Failed to parse XML response")
        .hasCauseInstanceOf(JAXBException.class);
  }

  @Test
  void parseXmlResponse_WhenEmptyResponse_ShouldThrowEntsoEClientException() throws Exception {
    // Given
    when(mockHttpClient.get(eq(baseUrl), any())).thenReturn("");

    // When & Then
    assertThatThrownBy(
            () ->
                client.getDayAheadLoadForecast(
                    AreaCode.FRANCE, LocalDateTime.now().minusDays(1), LocalDateTime.now(), null))
        .isInstanceOf(EntsoEClientException.class)
        .hasMessageContaining("Failed to parse XML response");
  }

  @Test
  void allMethods_WithNullOffset_ShouldNotIncludeOffsetInParameters() throws Exception {
    // Given
    when(mockHttpClient.get(eq(baseUrl), any())).thenReturn(validXmlResponse);

    LocalDateTime start = LocalDateTime.of(2025, 1, 1, 0, 0);
    LocalDateTime end = LocalDateTime.of(2025, 1, 2, 0, 0);

    // When - test all methods with null offset
    client.getActualTotalLoad(AreaCode.GERMANY, start, end, null);
    client.getDayAheadLoadForecast(AreaCode.GERMANY, start, end, null);
    client.getWeekAheadLoadForecast(AreaCode.GERMANY, start, end, null);
    client.getMonthAheadLoadForecast(AreaCode.GERMANY, start, end, null);
    client.getYearAheadLoadForecast(AreaCode.GERMANY, start, end, null);
    client.getYearAheadForecastMargin(AreaCode.GERMANY, start, end, null);

    // Then
    ArgumentCaptor<Map<String, String>> paramsCaptor = ArgumentCaptor.forClass(Map.class);
    verify(mockHttpClient, times(6)).get(eq(baseUrl), paramsCaptor.capture());

    // All captured parameter maps should not contain offset
    paramsCaptor.getAllValues().forEach(params -> assertThat(params).doesNotContainKey("offset"));
  }

  @Test
  void close_ShouldCloseHttpClient() {
    // When
    client.close();

    // Then
    verify(mockHttpClient).close();
  }

  @Test
  void constructor_ShouldInitializeSuccessfully() {
    // When & Then
    assertThatCode(() -> new DefaultEntsoEClient(mockHttpClient, baseUrl))
        .doesNotThrowAnyException();
  }

  @Test
  void constructor_WhenNullHttpClient_ShouldAcceptButFailOnClose() {
    // When
    DefaultEntsoEClient clientWithNullHttp = new DefaultEntsoEClient(null, baseUrl);

    // Then - close should not throw exception
    assertThatCode(() -> clientWithNullHttp.close()).doesNotThrowAnyException();
  }
}
