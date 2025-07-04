package org.example.model.load;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.EqualsAndHashCode;
import lombok.NoArgsConstructor;
import org.example.adapter.LocalDateTimeAdapter;
import org.example.model.common.TimeInterval;

import javax.xml.bind.annotation.XmlAccessType;
import javax.xml.bind.annotation.XmlAccessorType;
import javax.xml.bind.annotation.XmlElement;
import javax.xml.bind.annotation.adapters.XmlJavaTypeAdapter;

import java.time.LocalDateTime;

import static org.example.model.load.GLMarketDocument.XML_NAMESPACE;


@XmlAccessorType(XmlAccessType.FIELD)
@Data
@NoArgsConstructor
@AllArgsConstructor
public class LoadTimeInterval{

    @XmlElement(name = "start", namespace = XML_NAMESPACE)
    @XmlJavaTypeAdapter(LocalDateTimeAdapter.class)
    private LocalDateTime start;

    @XmlElement(name = "end", namespace = XML_NAMESPACE)
    @XmlJavaTypeAdapter(LocalDateTimeAdapter.class)
    private LocalDateTime end;
}
