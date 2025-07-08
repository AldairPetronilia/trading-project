package org.example.adapter;

import javax.xml.bind.annotation.adapters.XmlAdapter;
import org.example.model.common.MarketRoleType;

public class MarketRoleTypeAdapter extends XmlAdapter<String, MarketRoleType> {
  @Override
  public MarketRoleType unmarshal(String code) {
    return MarketRoleType.fromCode(code);
  }

  @Override
  public String marshal(MarketRoleType type) {
    return type.getCode();
  }
}
