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
}
