package org.example.utils;

import org.example.model.common.AreaCode;
import org.example.model.load.GLMarketDocument;
import org.example.model.load.LoadPeriod;
import org.example.model.load.LoadTimeSeries;
import org.example.model.load.QuantityPoint;

import javax.xml.bind.JAXBContext;
import javax.xml.bind.JAXBException;
import javax.xml.bind.Marshaller;
import javax.xml.bind.Unmarshaller;
import java.io.StringReader;
import java.io.StringWriter;

public class LoadDomainXmlParser {

    public static GLMarketDocument parseLoadDomainXml(String xmlContent) throws JAXBException, JAXBException {
        JAXBContext jaxbContext = JAXBContext.newInstance(GLMarketDocument.class);
        Unmarshaller unmarshaller = jaxbContext.createUnmarshaller();

        StringReader reader = new StringReader(xmlContent);
        return (GLMarketDocument) unmarshaller.unmarshal(reader);
    }

    public static String toXml(GLMarketDocument document) throws JAXBException {
        JAXBContext jaxbContext = JAXBContext.newInstance(GLMarketDocument.class);
        Marshaller marshaller = jaxbContext.createMarshaller();
        marshaller.setProperty(Marshaller.JAXB_FORMATTED_OUTPUT, true);

        StringWriter writer = new StringWriter();
        marshaller.marshal(document, writer);
        return writer.toString();
    }

    // Example usage demonstrating Load Domain response parsing
    public static void main(String[] args) {
        try {
            String loadResponseXml = "<!-- Your GL_MarketDocument XML here -->";
            GLMarketDocument document = parseLoadDomainXml(loadResponseXml);

            System.out.println("Document Type: " + document.getType().getDescription());
            System.out.println("Process Type: " + document.getProcessType().getDescription());
            System.out.println("Created: " + document.getCreatedDateTimeAsLocalDateTime());

            // Access time series data
            for (LoadTimeSeries series : document.getTimeSeries()) {
                System.out.println("Business Type: " + series.getBusinessType().getDescription());
                System.out.println("Object Aggregation: " + series.getObjectAggregation());
                System.out.println("Quantity Unit: " + series.getQuantityMeasureUnitName());

                // Access bidding zone
                if (series.getOutBiddingZoneDomainMRID() != null) {
                    AreaCode area = series.getOutBiddingZoneDomainMRID().getAreaCode();
                    if (area != null) {
                        System.out.println("Bidding Zone: " + area.getDescription());
                    }
                }

                // Access quantity data points
                for (LoadPeriod period : series.getPeriods()) {
                    System.out.println("Period: " + period.getTimeInterval().getStart() +
                            " to " + period.getTimeInterval().getEnd());
                    System.out.println("Resolution: " + period.getResolution());

                    for (QuantityPoint point : period.getPoints()) {
                        System.out.println("Position " + point.getPosition() +
                                ": " + point.getQuantity() + " " +
                                series.getQuantityMeasureUnitName());
                    }
                }
            }

        } catch (JAXBException e) {
            e.printStackTrace();
        }
    }
}
