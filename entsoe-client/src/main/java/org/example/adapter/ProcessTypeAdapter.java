package org.example.adapter;

import javax.xml.bind.annotation.adapters.XmlAdapter;
import org.example.model.common.ProcessType;

public class ProcessTypeAdapter extends XmlAdapter<String, ProcessType> {

  @Override
  public ProcessType unmarshal(String code) {
    return ProcessType.fromCode(code);
  }

  @Override
  public String marshal(ProcessType type) {
    return type.getCode();
  }
}
