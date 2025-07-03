package org.example.model;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import javax.xml.bind.annotation.XmlAccessType;
import javax.xml.bind.annotation.XmlAccessorType;
import javax.xml.bind.annotation.XmlElement;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;

// Time Interval class
@XmlAccessorType(XmlAccessType.FIELD)
@Data
@NoArgsConstructor
@AllArgsConstructor
public class TimeInterval {

    @XmlElement(name = "start")
    private String start;

    @XmlElement(name = "end")
    private String end;

    // Helper methods to get dates as LocalDateTime
    public LocalDateTime getStartAsLocalDateTime() {
        if (start != null) {
            return LocalDateTime.parse(start, DateTimeFormatter.ISO_DATE_TIME);
        }
        return null;
    }

    public LocalDateTime getEndAsLocalDateTime() {
        if (end != null) {
            return LocalDateTime.parse(end, DateTimeFormatter.ISO_DATE_TIME);
        }
        return null;
    }
}
