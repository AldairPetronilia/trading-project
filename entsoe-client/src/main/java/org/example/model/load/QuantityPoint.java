package org.example.model.load;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import javax.xml.bind.annotation.XmlAccessType;
import javax.xml.bind.annotation.XmlAccessorType;
import javax.xml.bind.annotation.XmlElement;

// Point class for Load Domain with quantity instead of price
@XmlAccessorType(XmlAccessType.FIELD)
@Data
@NoArgsConstructor
@AllArgsConstructor
public class QuantityPoint {

    @XmlElement(name = "position")
    private Integer position;

    @XmlElement(name = "quantity")
    private Double quantity;
}
