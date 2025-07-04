package org.example.model.common;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;
import org.example.adapter.AreaCodeAdapter;

import javax.xml.bind.annotation.XmlAccessType;
import javax.xml.bind.annotation.XmlAccessorType;
import javax.xml.bind.annotation.XmlAttribute;
import javax.xml.bind.annotation.XmlValue;
import javax.xml.bind.annotation.adapters.XmlJavaTypeAdapter;

@XmlAccessorType(XmlAccessType.FIELD)
@Data
@NoArgsConstructor
@AllArgsConstructor
public class DomainMRID {

    @XmlAttribute(name = "codingScheme")
    private String codingScheme;

    @XmlValue
    @XmlJavaTypeAdapter(AreaCodeAdapter.class)
    private AreaCode areaCode;

}
