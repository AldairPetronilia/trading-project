package org.example.adapter;

import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import javax.xml.bind.annotation.adapters.XmlAdapter;

public class LocalDateTimeAdapter extends XmlAdapter<String, LocalDateTime> {
  @Override
  public LocalDateTime unmarshal(String dateTime) throws Exception {
    return LocalDateTime.parse(dateTime, DateTimeFormatter.ISO_DATE_TIME);
  }

  @Override
  public String marshal(LocalDateTime localDateTime) throws Exception {
    return localDateTime.format(DateTimeFormatter.ISO_DATE_TIME);
  }
}
