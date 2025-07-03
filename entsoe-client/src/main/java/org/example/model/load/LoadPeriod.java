package org.example.model.load;

import lombok.Data;
import lombok.NoArgsConstructor;
import org.example.model.common.TimeInterval;

import javax.xml.bind.annotation.XmlAccessType;
import javax.xml.bind.annotation.XmlAccessorType;
import javax.xml.bind.annotation.XmlElement;
import java.util.List;

// Period class for Load Domain with quantity points
@XmlAccessorType(XmlAccessType.FIELD)
@Data
@NoArgsConstructor
public class LoadPeriod {

    @XmlElement(name = "timeInterval")
    private TimeInterval timeInterval;

    @XmlElement(name = "resolution")
    private String resolution;

    @XmlElement(name = "Point")
    private List<QuantityPoint> points;
}
