package org.example.model.common;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import javax.xml.bind.annotation.XmlAccessType;
import javax.xml.bind.annotation.XmlAccessorType;
import javax.xml.bind.annotation.XmlAttribute;
import javax.xml.bind.annotation.XmlValue;

@XmlAccessorType(XmlAccessType.FIELD)
@Data
@NoArgsConstructor
@AllArgsConstructor
public class DomainMRID {

    @XmlAttribute(name = "codingScheme")
    private String codingScheme;

    @XmlValue
    private String value;

    // Helper method to get the area code as enum
    public AreaCode getAreaCode() {
        try {
            return AreaCode.fromCode(value);
        } catch (IllegalArgumentException e) {
            return null; // Return null for unknown area codes
        }
    }

    // Helper method to set area code from enum
    public void setAreaCode(AreaCode areaCode) {
        this.value = areaCode != null ? areaCode.getCode() : null;
    }

    // Convenience constructor with AreaCode
    public DomainMRID(String codingScheme, AreaCode areaCode) {
        this.codingScheme = codingScheme;
        this.value = areaCode != null ? areaCode.getCode() : null;
    }
}
