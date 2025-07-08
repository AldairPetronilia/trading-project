package org.example.adapter;

import javax.xml.bind.annotation.adapters.XmlAdapter;
import org.example.model.common.BusinessType;

public class BusinessTypeAdapter extends XmlAdapter<String, BusinessType> {
  @Override
  public BusinessType unmarshal(String code) {
    return BusinessType.fromCode(code);
  }

  @Override
  public String marshal(BusinessType type) {
    return type.getCode();
  }
}
