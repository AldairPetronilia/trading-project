package org.example.utils;

import org.example.model.common.*;
import org.example.model.load.*;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.BeforeEach;
import static org.junit.jupiter.api.Assertions.*;
import javax.xml.bind.JAXBException;
import java.io.FileNotFoundException;
import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.time.LocalDateTime;

public class LoadDomainXmlParserTest {

    private LoadDomainXmlParser parser;

    @BeforeEach
    void setUp() {
        parser = new LoadDomainXmlParser();
    }

    @Test
    void testMinimalParsing() throws JAXBException, IOException {
        String fileName = "loadXmls/minimalLoadXml.xml";
        String minimalXml = loadXml(fileName);

        GLMarketDocument document = LoadDomainXmlParser.parseLoadDomainXml(minimalXml);

        assertNotNull(document, "Document should not be null");
        System.out.println("Document class: " + document.getClass());
        System.out.println("mRID value: '" + document.getMRID() + "'");

        assertEquals("test123", document.getMRID());
        assertEquals(Integer.valueOf(1), document.getRevisionNumber());
        assertEquals(DocumentType.SYSTEM_TOTAL_LOAD, document.getType());
    }

    @Test
    void testParseActualTotalLoad() throws JAXBException, IOException {
        String filename = "loadXmls/actualTotalLoad.xml";
        String actualTotalLoadXml = loadXml(filename);

        GLMarketDocument document = parser.parseLoadDomainXml(actualTotalLoadXml);

        // Assert document level fields
        assertEquals("5693afe33ce749e4b0cea17f1f64f211", document.getMRID());
        assertEquals(Integer.valueOf(1), document.getRevisionNumber());
        assertEquals(DocumentType.SYSTEM_TOTAL_LOAD, document.getType());
        assertEquals(ProcessType.REALISED, document.getProcessType());
        assertEquals(MarketRoleType.ISSUING_OFFICE, document.getSenderMarketParticipantMarketRoleType());
        assertEquals(MarketRoleType.MARKET_OPERATOR, document.getReceiverMarketParticipantMarketRoleType());

        // Assert created date time
        LocalDateTime expectedCreated = LocalDateTime.of(2016, 2, 26, 7, 24, 53);
        assertEquals(expectedCreated, document.getCreatedDateTime());

        // Assert time period
        LocalDateTime expectedStart = LocalDateTime.of(2015,12,31,23,0,0);
        LocalDateTime expectedEnd = LocalDateTime.of(2016,12,31,23,0,0);
        assertEquals(expectedStart, document.getTimePeriodTimeInterval().getStart());
        assertEquals(expectedEnd, document.getTimePeriodTimeInterval().getEnd());

        // Assert time series
        assertNotNull(document.getTimeSeries());

        LoadTimeSeries series = document.getTimeSeries();
        assertEquals("1", series.getMRID());
        assertEquals(BusinessType.CONSUMPTION, series.getBusinessType());
        assertEquals(ObjectAggregation.AGGREGATED, series.getObjectAggregation());
        assertEquals("MAW", series.getQuantityMeasureUnitName());
        assertEquals(CurveType.SEQUENTIAL_FIXED_SIZE_BLOCK, series.getCurveType());

        // Assert bidding zone
        assertEquals("A01", series.getOutBiddingZoneDomainMRID().getCodingScheme());
        assertEquals("10YCZ-CEPS-----N", series.getOutBiddingZoneDomainMRID().getAreaCode().getCode());
        assertEquals(AreaCode.CZECH_REPUBLIC, series.getOutBiddingZoneDomainMRID().getAreaCode());

        // Assert period and points
        LoadPeriod period = series.getPeriod();
        assertEquals("PT60M", period.getResolution());
        assertEquals(2, period.getPoints().size());

        QuantityPoint point1 = period.getPoints().getFirst();
        assertEquals(Integer.valueOf(1), point1.getPosition());
        assertEquals(Double.valueOf(6288), point1.getQuantity());

        QuantityPoint point2 = period.getPoints().get(1);
        assertEquals(Integer.valueOf(2), point2.getPosition());
        assertEquals(Double.valueOf(6350), point2.getQuantity());
    }

    @Test
    void testParseDayAheadLoadForecast() throws JAXBException, IOException {
        String filename = "loadXmls/dayAhead.xml";
        String dayAheadXml = loadXml(filename);

        GLMarketDocument document = parser.parseLoadDomainXml(dayAheadXml);

        assertEquals("8086330c19054ec18d7cb023f1541062", document.getMRID());
        assertEquals(DocumentType.SYSTEM_TOTAL_LOAD, document.getType());
        assertEquals(ProcessType.DAY_AHEAD, document.getProcessType());

        LoadTimeSeries series = document.getTimeSeries();
        assertEquals(BusinessType.CONSUMPTION, series.getBusinessType());

        LoadPeriod period = series.getPeriod();
        LocalDateTime expectedStart = LocalDateTime.of(2015, 12, 31, 23, 0, 0);
        LocalDateTime expectedEnd = LocalDateTime.of(2016, 1, 1, 23, 0, 0);
        assertEquals(expectedStart, period.getTimeInterval().getStart());
        assertEquals(expectedEnd, period.getTimeInterval().getEnd());
        assertEquals("PT60M", period.getResolution());

        // Verify first and last points
        assertEquals(Double.valueOf(6363), period.getPoints().get(0).getQuantity());
        assertEquals(Double.valueOf(6182), period.getPoints().get(1).getQuantity());
    }

    @Test
    void testParseWeekAheadLoadForecast() throws JAXBException, IOException {
        String filename = "loadXmls/weekAhead.xml";
        String weekAheadXml = loadXml(filename);

        GLMarketDocument document = parser.parseLoadDomainXml(weekAheadXml);

        assertEquals("5931be56ab5b47c79565629be03b9555", document.getMRID());
        assertEquals(ProcessType.WEEK_AHEAD, document.getProcessType());

        LoadTimeSeries series = document.getTimeSeries();
        assertEquals(BusinessType.MINIMUM_POSSIBLE, series.getBusinessType());

        LoadPeriod period = series.getPeriod();
        assertEquals("P1D", period.getResolution()); // Daily resolution for week-ahead
    }

    @Test
    void testParseYearAheadForecastMargin() throws JAXBException, IOException {
        String filename = "loadXmls/forecastMargin.xml";
        String forecastMarginXml = loadXml(filename);

        GLMarketDocument document = parser.parseLoadDomainXml(forecastMarginXml);

        // This is the Forecast Margin endpoint - different document type
        assertEquals("c4cdfa468d6741a08d0182794d2bf731", document.getMRID());
        assertEquals(DocumentType.LOAD_FORECAST_MARGIN, document.getType()); // A70
        assertEquals(ProcessType.YEAR_AHEAD, document.getProcessType());

        LoadTimeSeries series = document.getTimeSeries();
        assertEquals(BusinessType.NEGATIVE_FORECAST_MARGIN, series.getBusinessType()); // A92

        LoadPeriod period = series.getPeriod();
        assertEquals("P1Y", period.getResolution()); // Yearly resolution
        assertEquals(1, period.getPoints().size()); // Single data point for whole year
        assertEquals(Double.valueOf(2841), period.getPoints().get(0).getQuantity());
    }

    @Test
    void testParseInvalidXml() throws IOException {
        String filename = "loadXmls/invalid.xml";
        String invalidXml = loadXml(filename);

        assertThrows(JAXBException.class, () -> {
            parser.parseLoadDomainXml(invalidXml);
        });
    }

    @Test
    void testParseEmptyTimeSeries() throws JAXBException, IOException {
        String filename = "loadXmls/emptyTimeSeries.xml";
        String emptyTimeSeriesXml = loadXml(filename);

        GLMarketDocument document = parser.parseLoadDomainXml(emptyTimeSeriesXml);

        assertEquals("test123", document.getMRID());
        assertNull(document.getTimeSeries());
    }

    @Test
    void testAreaCodeMapping() throws JAXBException, IOException {
        String filename = "loadXmls/xmlWithDifferentArea.xml";
        String xmlWithDifferentArea = loadXml(filename);

        GLMarketDocument document = parser.parseLoadDomainXml(xmlWithDifferentArea);
        LoadTimeSeries series = document.getTimeSeries();

        // Test Germany area code mapping
        assertEquals(AreaCode.GERMANY, series.getOutBiddingZoneDomainMRID().getAreaCode());
    }

    @Test
    void testObjectAggregationEnum() throws JAXBException, IOException {
        // Test with enhanced LoadTimeSeries that has ObjectAggregation enum
        String filename = "loadXmls/xmlWithObjectAgg.xml";
        String xmlWithObjectAgg = loadXml(filename);

        GLMarketDocument document = parser.parseLoadDomainXml(xmlWithObjectAgg);
        LoadTimeSeries series = document.getTimeSeries();

        assertEquals(ObjectAggregation.AGGREGATED, series.getObjectAggregation());
    }

    private String loadXml(String filename) throws IOException {
        InputStream inputStream = getClass().getClassLoader().getResourceAsStream(filename);
        if (inputStream == null) {
            throw new FileNotFoundException(String.format("%s was not found", filename));
        }
        assertNotNull(inputStream, "Resource not found");
        return new String(inputStream.readAllBytes(), StandardCharsets.UTF_8);
    }
}
