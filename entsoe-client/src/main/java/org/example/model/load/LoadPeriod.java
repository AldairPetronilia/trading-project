package org.example.model.load;

import static org.example.model.load.GLMarketDocument.XML_NAMESPACE;

import java.util.List;
import javax.xml.bind.annotation.XmlAccessType;
import javax.xml.bind.annotation.XmlAccessorType;
import javax.xml.bind.annotation.XmlElement;
import lombok.Data;
import lombok.NoArgsConstructor;

// Period class for Load Domain with quantity points
@XmlAccessorType(XmlAccessType.FIELD)
@Data
@NoArgsConstructor
public class LoadPeriod {

  @XmlElement(name = "timeInterval", namespace = XML_NAMESPACE)
  private LoadTimeInterval timeInterval;

  @XmlElement(name = "resolution", namespace = XML_NAMESPACE)
  private String resolution;

  @XmlElement(name = "Point", namespace = XML_NAMESPACE)
  private List<QuantityPoint> points;
}
