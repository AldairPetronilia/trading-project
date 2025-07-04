package org.example.client;

import lombok.extern.slf4j.Slf4j;
import org.example.api.LoadDomainRequestBuilder;
import org.example.http.HttpClient;
import org.example.http.HttpClientException;
import org.example.model.common.AreaCode;
import org.example.model.common.EntsoEApiRequest;
import org.example.model.load.GLMarketDocument;

import javax.xml.bind.JAXBContext;
import javax.xml.bind.JAXBException;
import javax.xml.bind.Unmarshaller;
import java.io.StringReader;
import java.time.LocalDateTime;
import java.util.Map;

/**
 * Default implementation of EntsoEClient for ENTSO-E Transparency Platform Load Domain API
 * Provides HTTP-based access to load data and forecasts with XML response parsing
 */
@Slf4j
public class DefaultEntsoEClient implements EntsoEClient {

    private final HttpClient httpClient;
    private final String baseUrl;
    private final JAXBContext jaxbContext;

    /**
     * Creates a new DefaultEntsoEClient
     *
     * @param httpClient HTTP client for making requests
     * @param baseUrl Base URL of the ENTSO-E API endpoint
     */
    public DefaultEntsoEClient(HttpClient httpClient, String baseUrl) {
        this.httpClient = httpClient;
        this.baseUrl = baseUrl;
        try {
            this.jaxbContext = JAXBContext.newInstance(GLMarketDocument.class);
        } catch (JAXBException e) {
            throw new RuntimeException("Failed to initialize JAXB context", e);
        }
    }

    @Override
    public GLMarketDocument getActualTotalLoad(AreaCode biddingZone,
                                               LocalDateTime periodStart,
                                               LocalDateTime periodEnd,
                                               Integer offset) throws EntsoEClientException {

        log.debug("Fetching actual total load for zone: {}, period: {} to {}, offset: {}",
                biddingZone.getCode(), periodStart, periodEnd, offset);

        EntsoEApiRequest request = LoadDomainRequestBuilder.builder()
                .outBiddingZoneDomain(biddingZone)
                .periodStart(periodStart)
                .periodEnd(periodEnd)
                .offset(offset)
                .build()
                .buildActualTotalLoad();

        return executeRequest(request);
    }

    @Override
    public GLMarketDocument getDayAheadLoadForecast(AreaCode biddingZone,
                                                    LocalDateTime periodStart,
                                                    LocalDateTime periodEnd,
                                                    Integer offset) throws EntsoEClientException {

        log.debug("Fetching day-ahead load forecast for zone: {}, period: {} to {}, offset: {}",
                biddingZone.getCode(), periodStart, periodEnd, offset);

        EntsoEApiRequest request = LoadDomainRequestBuilder.builder()
                .outBiddingZoneDomain(biddingZone)
                .periodStart(periodStart)
                .periodEnd(periodEnd)
                .offset(offset)
                .build()
                .buildDayAheadLoadForecast();

        return executeRequest(request);
    }

    @Override
    public GLMarketDocument getWeekAheadLoadForecast(AreaCode biddingZone,
                                                     LocalDateTime periodStart,
                                                     LocalDateTime periodEnd,
                                                     Integer offset) throws EntsoEClientException {

        log.debug("Fetching week-ahead load forecast for zone: {}, period: {} to {}, offset: {}",
                biddingZone.getCode(), periodStart, periodEnd, offset);

        EntsoEApiRequest request = LoadDomainRequestBuilder.builder()
                .outBiddingZoneDomain(biddingZone)
                .periodStart(periodStart)
                .periodEnd(periodEnd)
                .offset(offset)
                .build()
                .buildWeekAheadLoadForecast();

        return executeRequest(request);
    }

    @Override
    public GLMarketDocument getMonthAheadLoadForecast(AreaCode biddingZone,
                                                      LocalDateTime periodStart,
                                                      LocalDateTime periodEnd,
                                                      Integer offset) throws EntsoEClientException {

        log.debug("Fetching month-ahead load forecast for zone: {}, period: {} to {}, offset: {}",
                biddingZone.getCode(), periodStart, periodEnd, offset);

        EntsoEApiRequest request = LoadDomainRequestBuilder.builder()
                .outBiddingZoneDomain(biddingZone)
                .periodStart(periodStart)
                .periodEnd(periodEnd)
                .offset(offset)
                .build()
                .buildMonthAheadLoadForecast();

        return executeRequest(request);
    }

    @Override
    public GLMarketDocument getYearAheadLoadForecast(AreaCode biddingZone,
                                                     LocalDateTime periodStart,
                                                     LocalDateTime periodEnd,
                                                     Integer offset) throws EntsoEClientException {

        log.debug("Fetching year-ahead load forecast for zone: {}, period: {} to {}, offset: {}",
                biddingZone.getCode(), periodStart, periodEnd, offset);

        EntsoEApiRequest request = LoadDomainRequestBuilder.builder()
                .outBiddingZoneDomain(biddingZone)
                .periodStart(periodStart)
                .periodEnd(periodEnd)
                .offset(offset)
                .build()
                .buildYearAheadLoadForecast();

        return executeRequest(request);
    }

    @Override
    public GLMarketDocument getYearAheadForecastMargin(AreaCode biddingZone,
                                                       LocalDateTime periodStart,
                                                       LocalDateTime periodEnd,
                                                       Integer offset) throws EntsoEClientException {

        log.debug("Fetching year-ahead forecast margin for zone: {}, period: {} to {}, offset: {}",
                biddingZone.getCode(), periodStart, periodEnd, offset);

        EntsoEApiRequest request = LoadDomainRequestBuilder.builder()
                .outBiddingZoneDomain(biddingZone)
                .periodStart(periodStart)
                .periodEnd(periodEnd)
                .offset(offset)
                .build()
                .buildYearAheadForecastMargin();

        return executeRequest(request);
    }

    /**
     * Common method to execute any API request and parse the XML response
     *
     * @param request The API request to execute
     * @return Parsed market document
     * @throws EntsoEClientException if the request fails or response cannot be parsed
     */
    private GLMarketDocument executeRequest(EntsoEApiRequest request) throws EntsoEClientException {
        try {
            Map<String, String> queryParams = request.toParameterMap();
            String xmlResponse = httpClient.get(baseUrl, queryParams);

            log.debug("Received XML response, parsing...");
            return parseXmlResponse(xmlResponse);

        } catch (HttpClientException e) {
            log.error("HTTP request failed for request: {}", request, e);
            throw new EntsoEClientException("Failed to fetch load data", e);
        } catch (JAXBException e) {
            log.error("XML parsing failed", e);
            throw new EntsoEClientException("Failed to parse XML response", e);
        }
    }

    /**
     * Parses XML response into GLMarketDocument
     *
     * @param xmlContent XML content to parse
     * @return Parsed market document
     * @throws JAXBException if XML parsing fails
     */
    private GLMarketDocument parseXmlResponse(String xmlContent) throws JAXBException {
        Unmarshaller unmarshaller = jaxbContext.createUnmarshaller();
        StringReader reader = new StringReader(xmlContent);
        return (GLMarketDocument) unmarshaller.unmarshal(reader);
    }

    @Override
    public void close() {
        if (httpClient != null) {
            httpClient.close();
            log.debug("EntsoE client closed");
        }
    }
}
