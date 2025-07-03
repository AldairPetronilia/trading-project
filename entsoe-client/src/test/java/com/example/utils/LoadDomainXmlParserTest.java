package com.example.utils;

import org.example.model.common.*;
import org.example.model.load.GLMarketDocument;
import org.example.model.load.LoadPeriod;
import org.example.model.load.LoadTimeSeries;
import org.example.model.load.QuantityPoint;
import org.example.utils.LoadDomainXmlParser;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.BeforeEach;
import static org.junit.jupiter.api.Assertions.*;
import javax.xml.bind.JAXBException;
import java.time.LocalDateTime;

public class LoadDomainXmlParserTest {

    private LoadDomainXmlParser parser;

    @BeforeEach
    void setUp() {
        parser = new LoadDomainXmlParser();
    }

    @Test
    void testMinimalParsing() throws JAXBException {
        String minimalXml = """
        <?xml version="1.0" encoding="UTF-8"?>
        <GL_MarketDocument xmlns="urn:iec62325.351:tc57wg16:451-6:generationloaddocument:3:0">
            <mRID>test123</mRID>
            <revisionNumber>1</revisionNumber>
            <type>A65</type>
        </GL_MarketDocument>
        """;

        GLMarketDocument document = LoadDomainXmlParser.parseLoadDomainXml(minimalXml);

        assertNotNull(document, "Document should not be null");
        System.out.println("Document class: " + document.getClass());
        System.out.println("mRID value: '" + document.getMRID() + "'");

        assertEquals("test123", document.getMRID());
        assertEquals(Integer.valueOf(1), document.getRevisionNumber());
        assertEquals(DocumentType.SYSTEM_TOTAL_LOAD, document.getType());
    }

    @Test
    void testParseActualTotalLoad() throws JAXBException {
        String actualTotalLoadXml = """
            <?xml version="1.0" encoding="UTF-8"?>
            <GL_MarketDocument xmlns="urn:iec62325.351:tc57wg16:451-6:generationloaddocument:3:0">
                <mRID>5693afe33ce749e4b0cea17f1f64f211</mRID>
                <revisionNumber>1</revisionNumber>
                <type>A65</type>
                <process.processType>A16</process.processType>
                <sender_MarketParticipant.mRID codingScheme="A01">10X1001A1001A450</sender_MarketParticipant.mRID>
                <sender_MarketParticipant.marketRole.type>A32</sender_MarketParticipant.marketRole.type>
                <receiver_MarketParticipant.mRID codingScheme="A01">10X1001A1001A450</receiver_MarketParticipant.mRID>
                <receiver_MarketParticipant.marketRole.type>A33</receiver_MarketParticipant.marketRole.type>
                <createdDateTime>2016-02-26T07:24:53Z</createdDateTime>
                <time_Period.timeInterval>
                    <start>2015-12-31T23:00Z</start>
                    <end>2016-12-31T23:00Z</end>
                </time_Period.timeInterval>
                <TimeSeries>
                    <mRID>1</mRID>
                    <businessType>A04</businessType>
                    <objectAggregation>A01</objectAggregation>
                    <outBiddingZone_Domain.mRID codingScheme="A01">10YCZ-CEPS-----N</outBiddingZone_Domain.mRID>
                    <quantity_Measure_Unit.name>MAW</quantity_Measure_Unit.name>
                    <curveType>A01</curveType>
                    <Period>
                        <timeInterval>
                            <start>2015-12-31T23:00Z</start>
                            <end>2016-12-31T23:00Z</end>
                        </timeInterval>
                        <resolution>PT60M</resolution>
                        <Point>
                            <position>1</position>
                            <quantity>6288</quantity>
                        </Point>
                        <Point>
                            <position>2</position>
                            <quantity>6350</quantity>
                        </Point>
                    </Period>
                </TimeSeries>
            </GL_MarketDocument>
            """;

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
        assertEquals(expectedCreated, document.getCreatedDateTimeAsLocalDateTime());

        // Assert time period
        assertEquals("2015-12-31T23:00Z", document.getTimePeriodTimeInterval().getStart());
        assertEquals("2016-12-31T23:00Z", document.getTimePeriodTimeInterval().getEnd());

        // Assert time series
        assertNotNull(document.getTimeSeries());
        assertEquals(1, document.getTimeSeries().size());

        LoadTimeSeries series = document.getTimeSeries().get(0);
        assertEquals("1", series.getMRID());
        assertEquals(BusinessType.CONSUMPTION, series.getBusinessType());
        assertEquals("A01", series.getObjectAggregation());
        assertEquals("MAW", series.getQuantityMeasureUnitName());
        assertEquals(CurveType.SEQUENTIAL_FIXED_SIZE_BLOCK, series.getCurveType());

        // Assert bidding zone
        assertEquals("A01", series.getOutBiddingZoneDomainMRID().getCodingScheme());
        assertEquals("10YCZ-CEPS-----N", series.getOutBiddingZoneDomainMRID().getValue());
        assertEquals(AreaCode.CZECH_REPUBLIC, series.getOutBiddingZoneDomainMRID().getAreaCode());

        // Assert period and points
        assertEquals(1, series.getPeriods().size());
        LoadPeriod period = series.getPeriods().get(0);
        assertEquals("PT60M", period.getResolution());
        assertEquals(2, period.getPoints().size());

        QuantityPoint point1 = period.getPoints().get(0);
        assertEquals(Integer.valueOf(1), point1.getPosition());
        assertEquals(Double.valueOf(6288), point1.getQuantity());

        QuantityPoint point2 = period.getPoints().get(1);
        assertEquals(Integer.valueOf(2), point2.getPosition());
        assertEquals(Double.valueOf(6350), point2.getQuantity());
    }

    @Test
    void testParseDayAheadLoadForecast() throws JAXBException {
        String dayAheadXml = """
            <GL_MarketDocument xmlns="urn:iec62325.351:tc57wg16:451-6:generationloaddocument:3:0">
                <mRID>8086330c19054ec18d7cb023f1541062</mRID>
                <revisionNumber>1</revisionNumber>
                <type>A65</type>
                <process.processType>A01</process.processType>
                <sender_MarketParticipant.mRID codingScheme="A01">10X1001A1001A450</sender_MarketParticipant.mRID>
                <sender_MarketParticipant.marketRole.type>A32</sender_MarketParticipant.marketRole.type>
                <receiver_MarketParticipant.mRID codingScheme="A01">10X1001A1001A450</receiver_MarketParticipant.mRID>
                <receiver_MarketParticipant.marketRole.type>A33</receiver_MarketParticipant.marketRole.type>
                <createdDateTime>2016-05-10T08:08:24Z</createdDateTime>
                <time_Period.timeInterval>
                    <start>2015-12-31T23:00Z</start>
                    <end>2016-12-31T23:00Z</end>
                </time_Period.timeInterval>
                <TimeSeries>
                    <mRID>1</mRID>
                    <businessType>A04</businessType>
                    <objectAggregation>A01</objectAggregation>
                    <outBiddingZone_Domain.mRID codingScheme="A01">10YCZ-CEPS-----N</outBiddingZone_Domain.mRID>
                    <quantity_Measure_Unit.name>MAW</quantity_Measure_Unit.name>
                    <curveType>A01</curveType>
                    <Period>
                        <timeInterval>
                            <start>2015-12-31T23:00Z</start>
                            <end>2016-01-01T23:00Z</end>
                        </timeInterval>
                        <resolution>PT60M</resolution>
                        <Point>
                            <position>1</position>
                            <quantity>6363</quantity>
                        </Point>
                        <Point>
                            <position>24</position>
                            <quantity>6182</quantity>
                        </Point>
                    </Period>
                </TimeSeries>
            </GL_MarketDocument>
            """;

        GLMarketDocument document = parser.parseLoadDomainXml(dayAheadXml);

        assertEquals("8086330c19054ec18d7cb023f1541062", document.getMRID());
        assertEquals(DocumentType.SYSTEM_TOTAL_LOAD, document.getType());
        assertEquals(ProcessType.DAY_AHEAD, document.getProcessType());

        LoadTimeSeries series = document.getTimeSeries().get(0);
        assertEquals(BusinessType.CONSUMPTION, series.getBusinessType());

        LoadPeriod period = series.getPeriods().get(0);
        assertEquals("2015-12-31T23:00Z", period.getTimeInterval().getStart());
        assertEquals("2016-01-01T23:00Z", period.getTimeInterval().getEnd());
        assertEquals("PT60M", period.getResolution());

        // Verify first and last points
        assertEquals(Double.valueOf(6363), period.getPoints().get(0).getQuantity());
        assertEquals(Double.valueOf(6182), period.getPoints().get(1).getQuantity());
    }

    @Test
    void testParseWeekAheadLoadForecast() throws JAXBException {
        String weekAheadXml = """
            <GL_MarketDocument xmlns="urn:iec62325.351:tc57wg16:451-6:generationloaddocument:3:0">
                <mRID>5931be56ab5b47c79565629be03b9555</mRID>
                <revisionNumber>1</revisionNumber>
                <type>A65</type>
                <process.processType>A31</process.processType>
                <sender_MarketParticipant.mRID codingScheme="A01">10X1001A1001A450</sender_MarketParticipant.mRID>
                <sender_MarketParticipant.marketRole.type>A32</sender_MarketParticipant.marketRole.type>
                <receiver_MarketParticipant.mRID codingScheme="A01">10X1001A1001A450</receiver_MarketParticipant.mRID>
                <receiver_MarketParticipant.marketRole.type>A33</receiver_MarketParticipant.marketRole.type>
                <createdDateTime>2016-05-10T08:16:57Z</createdDateTime>
                <time_Period.timeInterval>
                    <start>2015-12-27T23:00Z</start>
                    <end>2016-04-10T22:00Z</end>
                </time_Period.timeInterval>
                <TimeSeries>
                    <mRID>1</mRID>
                    <businessType>A60</businessType>
                    <objectAggregation>A01</objectAggregation>
                    <outBiddingZone_Domain.mRID codingScheme="A01">10YCZ-CEPS-----N</outBiddingZone_Domain.mRID>
                    <quantity_Measure_Unit.name>MAW</quantity_Measure_Unit.name>
                    <curveType>A01</curveType>
                    <Period>
                        <timeInterval>
                            <start>2015-12-27T23:00Z</start>
                            <end>2016-01-03T23:00Z</end>
                        </timeInterval>
                        <resolution>P1D</resolution>
                        <Point>
                            <position>1</position>
                            <quantity>6050</quantity>
                        </Point>
                        <Point>
                            <position>7</position>
                            <quantity>6156</quantity>
                        </Point>
                    </Period>
                </TimeSeries>
            </GL_MarketDocument>
            """;

        GLMarketDocument document = parser.parseLoadDomainXml(weekAheadXml);

        assertEquals("5931be56ab5b47c79565629be03b9555", document.getMRID());
        assertEquals(ProcessType.WEEK_AHEAD, document.getProcessType());

        LoadTimeSeries series = document.getTimeSeries().get(0);
        assertEquals(BusinessType.MINIMUM_POSSIBLE, series.getBusinessType());

        LoadPeriod period = series.getPeriods().get(0);
        assertEquals("P1D", period.getResolution()); // Daily resolution for week-ahead
    }

    @Test
    void testParseYearAheadForecastMargin() throws JAXBException {
        String forecastMarginXml = """
            <GL_MarketDocument xmlns="urn:iec62325.351:tc57wg16:451-6:generationloaddocument:3:0">
                <mRID>c4cdfa468d6741a08d0182794d2bf731</mRID>
                <revisionNumber>1</revisionNumber>
                <type>A70</type>
                <process.processType>A33</process.processType>
                <sender_MarketParticipant.mRID codingScheme="A01">10X1001A1001A450</sender_MarketParticipant.mRID>
                <sender_MarketParticipant.marketRole.type>A32</sender_MarketParticipant.marketRole.type>
                <receiver_MarketParticipant.mRID codingScheme="A01">10X1001A1001A450</receiver_MarketParticipant.mRID>
                <receiver_MarketParticipant.marketRole.type>A33</receiver_MarketParticipant.marketRole.type>
                <createdDateTime>2016-05-10T08:19:40Z</createdDateTime>
                <time_Period.timeInterval>
                    <start>2015-12-31T23:00Z</start>
                    <end>2016-12-31T23:00Z</end>
                </time_Period.timeInterval>
                <TimeSeries>
                    <mRID>1</mRID>
                    <businessType>A92</businessType>
                    <objectAggregation>A01</objectAggregation>
                    <outBiddingZone_Domain.mRID codingScheme="A01">10YCZ-CEPS-----N</outBiddingZone_Domain.mRID>
                    <quantity_Measure_Unit.name>MAW</quantity_Measure_Unit.name>
                    <curveType>A01</curveType>
                    <Period>
                        <timeInterval>
                            <start>2015-12-31T23:00Z</start>
                            <end>2016-12-31T23:00Z</end>
                        </timeInterval>
                        <resolution>P1Y</resolution>
                        <Point>
                            <position>1</position>
                            <quantity>2841</quantity>
                        </Point>
                    </Period>
                </TimeSeries>
            </GL_MarketDocument>
            """;

        GLMarketDocument document = parser.parseLoadDomainXml(forecastMarginXml);

        // This is the Forecast Margin endpoint - different document type
        assertEquals("c4cdfa468d6741a08d0182794d2bf731", document.getMRID());
        assertEquals(DocumentType.LOAD_FORECAST_MARGIN, document.getType()); // A70
        assertEquals(ProcessType.YEAR_AHEAD, document.getProcessType());

        LoadTimeSeries series = document.getTimeSeries().get(0);
        assertEquals(BusinessType.NEGATIVE_FORECAST_MARGIN, series.getBusinessType()); // A92

        LoadPeriod period = series.getPeriods().get(0);
        assertEquals("P1Y", period.getResolution()); // Yearly resolution
        assertEquals(1, period.getPoints().size()); // Single data point for whole year
        assertEquals(Double.valueOf(2841), period.getPoints().get(0).getQuantity());
    }

    @Test
    void testParseInvalidXml() {
        String invalidXml = """
            <InvalidDocument>
                <somefield>value</somefield>
            </InvalidDocument>
            """;

        assertThrows(JAXBException.class, () -> {
            parser.parseLoadDomainXml(invalidXml);
        });
    }

    @Test
    void testParseEmptyTimeSeries() throws JAXBException {
        String emptyTimeSeriesXml = """
            <GL_MarketDocument xmlns="urn:iec62325.351:tc57wg16:451-6:generationloaddocument:3:0">
                <mRID>test123</mRID>
                <revisionNumber>1</revisionNumber>
                <type>A65</type>
                <process.processType>A16</process.processType>
                <sender_MarketParticipant.mRID codingScheme="A01">10X1001A1001A450</sender_MarketParticipant.mRID>
                <sender_MarketParticipant.marketRole.type>A32</sender_MarketParticipant.marketRole.type>
                <receiver_MarketParticipant.mRID codingScheme="A01">10X1001A1001A450</receiver_MarketParticipant.mRID>
                <receiver_MarketParticipant.marketRole.type>A33</receiver_MarketParticipant.marketRole.type>
                <createdDateTime>2016-02-26T07:24:53Z</createdDateTime>
                <time_Period.timeInterval>
                    <start>2015-12-31T23:00Z</start>
                    <end>2016-12-31T23:00Z</end>
                </time_Period.timeInterval>
            </GL_MarketDocument>
            """;

        GLMarketDocument document = parser.parseLoadDomainXml(emptyTimeSeriesXml);

        assertEquals("test123", document.getMRID());
        assertTrue(document.getTimeSeries() == null || document.getTimeSeries().isEmpty());
    }

    @Test
    void testAreaCodeMapping() throws JAXBException {
        String xmlWithDifferentArea = """
            <GL_MarketDocument xmlns="urn:iec62325.351:tc57wg16:451-6:generationloaddocument:3:0">
                <mRID>test123</mRID>
                <revisionNumber>1</revisionNumber>
                <type>A65</type>
                <process.processType>A16</process.processType>
                <sender_MarketParticipant.mRID codingScheme="A01">10X1001A1001A450</sender_MarketParticipant.mRID>
                <sender_MarketParticipant.marketRole.type>A32</sender_MarketParticipant.marketRole.type>
                <receiver_MarketParticipant.mRID codingScheme="A01">10X1001A1001A450</receiver_MarketParticipant.mRID>
                <receiver_MarketParticipant.marketRole.type>A33</receiver_MarketParticipant.marketRole.type>
                <createdDateTime>2016-02-26T07:24:53Z</createdDateTime>
                <time_Period.timeInterval>
                    <start>2015-12-31T23:00Z</start>
                    <end>2016-12-31T23:00Z</end>
                </time_Period.timeInterval>
                <TimeSeries>
                    <mRID>1</mRID>
                    <businessType>A04</businessType>
                    <objectAggregation>A01</objectAggregation>
                    <outBiddingZone_Domain.mRID codingScheme="A01">10Y1001A1001A83F</outBiddingZone_Domain.mRID>
                    <quantity_Measure_Unit.name>MAW</quantity_Measure_Unit.name>
                    <curveType>A01</curveType>
                    <Period>
                        <timeInterval>
                            <start>2015-12-31T23:00Z</start>
                            <end>2016-12-31T23:00Z</end>
                        </timeInterval>
                        <resolution>PT60M</resolution>
                        <Point>
                            <position>1</position>
                            <quantity>6288</quantity>
                        </Point>
                    </Period>
                </TimeSeries>
            </GL_MarketDocument>
            """;

        GLMarketDocument document = parser.parseLoadDomainXml(xmlWithDifferentArea);
        LoadTimeSeries series = document.getTimeSeries().get(0);

        // Test Germany area code mapping
        assertEquals("10Y1001A1001A83F", series.getOutBiddingZoneDomainMRID().getValue());
        assertEquals(AreaCode.GERMANY, series.getOutBiddingZoneDomainMRID().getAreaCode());
        assertTrue(series.getOutBiddingZoneDomainMRID().getAreaCode().hasAreaType(AreaType.BZN));
    }

    @Test
    void testObjectAggregationEnum() throws JAXBException {
        // Test with enhanced LoadTimeSeries that has ObjectAggregation enum
        String xmlWithObjectAgg = """
            <GL_MarketDocument xmlns="urn:iec62325.351:tc57wg16:451-6:generationloaddocument:3:0">
                <mRID>test123</mRID>
                <revisionNumber>1</revisionNumber>
                <type>A65</type>
                <process.processType>A16</process.processType>
                <sender_MarketParticipant.mRID codingScheme="A01">10X1001A1001A450</sender_MarketParticipant.mRID>
                <sender_MarketParticipant.marketRole.type>A32</sender_MarketParticipant.marketRole.type>
                <receiver_MarketParticipant.mRID codingScheme="A01">10X1001A1001A450</receiver_MarketParticipant.mRID>
                <receiver_MarketParticipant.marketRole.type>A33</receiver_MarketParticipant.marketRole.type>
                <createdDateTime>2016-02-26T07:24:53Z</createdDateTime>
                <TimeSeries>
                    <mRID>1</mRID>
                    <businessType>A04</businessType>
                    <objectAggregation>A01</objectAggregation>
                    <outBiddingZone_Domain.mRID codingScheme="A01">10YCZ-CEPS-----N</outBiddingZone_Domain.mRID>
                    <quantity_Measure_Unit.name>MAW</quantity_Measure_Unit.name>
                    <curveType>A01</curveType>
                </TimeSeries>
            </GL_MarketDocument>
            """;

        GLMarketDocument document = parser.parseLoadDomainXml(xmlWithObjectAgg);
        LoadTimeSeries series = document.getTimeSeries().get(0);

        // If using LoadTimeSeriesEnhanced with ObjectAggregation enum
        assertEquals("A01", series.getObjectAggregation());
        // assertEquals(ObjectAggregation.AGGREGATED, series.getObjectAggregation()); // If using enum version
    }
}
