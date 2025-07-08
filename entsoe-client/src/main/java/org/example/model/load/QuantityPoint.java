package org.example.model.load;

import static org.example.model.load.GLMarketDocument.XML_NAMESPACE;

import javax.xml.bind.annotation.XmlAccessType;
import javax.xml.bind.annotation.XmlAccessorType;
import javax.xml.bind.annotation.XmlElement;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

// Point class for Load Domain with quantity instead of price
@XmlAccessorType(XmlAccessType.FIELD)
@Data
@NoArgsConstructor
@AllArgsConstructor
public class QuantityPoint {

  @XmlElement(name = "position", namespace = XML_NAMESPACE)
  private Integer position;

  @XmlElement(name = "quantity", namespace = XML_NAMESPACE)
  private Double quantity;
}
