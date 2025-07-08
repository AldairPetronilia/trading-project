package org.example.adapter;

import javax.xml.bind.annotation.adapters.XmlAdapter;
import org.example.model.load.ObjectAggregation;

// XML Adapter for ObjectAggregation
public class ObjectAggregationAdapter extends XmlAdapter<String, ObjectAggregation> {
  @Override
  public ObjectAggregation unmarshal(String code) {
    try {
      return ObjectAggregation.fromCode(code);
    } catch (IllegalArgumentException e) {
      return null;
    }
  }

  @Override
  public String marshal(ObjectAggregation type) {
    return type != null ? type.getCode() : null;
  }
}
