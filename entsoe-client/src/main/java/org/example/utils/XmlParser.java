package org.example.utils;

import org.example.model.*;

import javax.xml.bind.JAXBContext;
import javax.xml.bind.JAXBException;
import javax.xml.bind.Marshaller;
import javax.xml.bind.Unmarshaller;
import java.io.StringReader;
import java.io.StringWriter;

public class XmlParser {

    public static PublicationMarketDocument parseXml(String xmlContent) throws JAXBException {
        JAXBContext jaxbContext = JAXBContext.newInstance(PublicationMarketDocument.class);
        Unmarshaller unmarshaller = jaxbContext.createUnmarshaller();

        StringReader reader = new StringReader(xmlContent);
        return (PublicationMarketDocument) unmarshaller.unmarshal(reader);
    }

    public static String toXml(PublicationMarketDocument document) throws JAXBException {
        JAXBContext jaxbContext = JAXBContext.newInstance(PublicationMarketDocument.class);
        Marshaller marshaller = jaxbContext.createMarshaller();
        marshaller.setProperty(Marshaller.JAXB_FORMATTED_OUTPUT, true);

        StringWriter writer = new StringWriter();
        marshaller.marshal(document, writer);
        return writer.toString();
    }

    // Example usage demonstrating type safety and enum usage
    public static void main(String[] args) {
        try {
            String xmlContent = "<!-- Your XML content here -->";
            PublicationMarketDocument document = parseXml(xmlContent);

            // Access typed enum values instead of raw strings
            System.out.println("Document Type: " + document.getType().getDescription());
            System.out.println("Document Code: " + document.getType().getCode());

            TimeSeries series = document.getTimeSeries();
            System.out.println("Business Type: " + series.getBusinessType().getDescription());
            System.out.println("Auction Type: " + series.getAuctionType().getDescription());
            System.out.println("Contract Type: " + series.getContractMarketAgreementType().getDescription());
            System.out.println("Curve Type: " + series.getCurveType().getDescription());

            System.out.println("Currency: " + series.getCurrencyUnitName());
            System.out.println("Price Unit: " + series.getPriceMeasureUnitName());

            // Access individual price points
            System.out.println("Number of price points: " + series.getPeriod().getPoints().size());
            for (Point point : series.getPeriod().getPoints()) {
                System.out.println("Position " + point.getPosition() +
                        ": " + point.getPriceAmount() + " " + series.getCurrencyUnitName() + "/" + series.getPriceMeasureUnitName());
            }

            // Example of creating objects programmatically with type safety
            PublicationMarketDocument newDoc = new PublicationMarketDocument();
            newDoc.setType(DocumentType.ALLOCATION_RESULT_DOCUMENT);
            newDoc.setSenderMarketParticipantMarketRoleType(MarketRoleType.ISSUING_OFFICE);

            TimeSeries newSeries = new TimeSeries();
            newSeries.setBusinessType(BusinessType.GENERAL_CAPACITY_INFORMATION);
            newSeries.setAuctionType(AuctionType.IMPLICIT);
            newSeries.setContractMarketAgreementType(ContractMarketAgreementType.INTRADAY);
            newSeries.setCurveType(CurveType.SEQUENTIAL_FIXED_SIZE_BLOCK);

            System.out.println("Created document with type: " + newDoc.getType().getDescription());

        } catch (JAXBException e) {
            e.printStackTrace();
        }
    }
}
