package org.example.model.publication;

import java.util.List;
import javax.xml.bind.annotation.XmlAccessType;
import javax.xml.bind.annotation.XmlAccessorType;
import javax.xml.bind.annotation.XmlElement;
import lombok.Data;
import lombok.NoArgsConstructor;
import org.example.model.common.TimeInterval;

// Period class
@XmlAccessorType(XmlAccessType.FIELD)
@Data
@NoArgsConstructor
public class Period {

  @XmlElement(name = "timeInterval")
  private TimeInterval timeInterval;

  @XmlElement(name = "resolution")
  private String resolution;

  @XmlElement(name = "Point")
  private List<Point> points;
}
