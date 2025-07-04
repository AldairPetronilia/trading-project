package org.example.model.common;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import javax.xml.bind.annotation.XmlAccessType;
import javax.xml.bind.annotation.XmlAccessorType;
import javax.xml.bind.annotation.XmlElement;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;

// Time Interval class
@Data
@NoArgsConstructor
@AllArgsConstructor
public abstract class TimeInterval {

    protected String start;

    protected String end;

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
