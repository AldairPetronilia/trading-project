package org.example.adapter;

import javax.xml.bind.annotation.adapters.XmlAdapter;
import org.example.model.common.AuctionType;

public class AuctionTypeAdapter extends XmlAdapter<String, AuctionType> {
  @Override
  public AuctionType unmarshal(String code) {
    return AuctionType.fromCode(code);
  }

  @Override
  public String marshal(AuctionType type) {
    return type.getCode();
  }
}
