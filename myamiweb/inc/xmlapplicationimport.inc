<?php

/**
 *	The Leginon software is Copyright under 
 *	Apache License, Version 2.0
 *	For terms of the license agreement see
 *	@license http://leginon.org
 */

/**
 *  This class convert a Leginon application.xml file 
 *  into:
 *      - SQL statements 
 *      - PHP array
 */
class XMLImport {

	var $definition;
	var $data;
	var $definitionqueries;
	var $insertqueries;
	var $fieldtypes;
	var $fieldvalues;

	function importXML($inputdata) {
		// --- try to read a XML file or a XML string
		$data = (@is_file($inputdata)) ? implode("",file($inputdata)) : $inputdata;
		$parser = xml_parser_create();
		xml_parser_set_option($parser,XML_OPTION_CASE_FOLDING,0);
		xml_parser_set_option($parser,XML_OPTION_SKIP_WHITE,1);
		xml_parse_into_struct($parser,$data,$values,$tags);
		xml_parser_free($parser);

		// --- Generate an array for the definition,
		// --- and one for the application data.
		foreach ($tags as $key=>$val) {
			if ($key == "definition") {
				$offset = $val[0];
				$length = $val[1]-$offset;
				$this->definition = (array_slice($values,$offset,$length));
			} else if ($key == "data") {
				$offset = $val[0];
				$length = $val[1]-$offset;
				$this->data = (array_slice($values,$offset,$length));
			}
		}
	}

	function XMLDefinition2SQL() {
		$values = $this->definition;
		foreach ((array)$values as $v) {
			if ($v['tag']=='sqltable' && $v['type']=='open') {
				$tablename = $v['attributes']['name'];
				$sqldef = "CREATE TABLE IF NOT EXISTS $tablename  ";
				$fields = array();
				$fieldtypes = array();
			}
			if ($v['tag']=='field') {
				$fname = $v['attributes']['name'];
				$ftype = $v['attributes']['type'];
				if ($v['attributes']['default'] == "0") {
					// 0 default for integer is considered as empty.
					// treat it properly here to set default
					$fdefault = "default '0'";
				} else {
					$fdefault = empty($v['attributes']['default']) ? '' : $v['attributes']['default'];
				}
				$fdefault = (!empty($fdefault) && strpos(strtolower($fdefault),'default')===false) ? 'default '.$fdefault : $fdefault;
				if ($fdefault=="DEFAULT 'CURRENT_TIMESTAMP'") $fdefault="DEFAULT CURRENT_TIMESTAMP";
				$fnull = (empty($fdefault) && empty($v['attributes']['null'])) ? 'null' : $v['attributes']['null'];
				// refs #9187 mariadb output conversion to mysql 5.6 compatible
				if ($fdefault=="DEFAULT CURRENT_TIMESTAMP" && $v['attributes']['extra'] && $v['attributes']['extra']=='DEFAULT_GENERATED') {
					$fextra ="ON UPDATE CURRENT_TIMESTAMP ";
				} else {
					$fextra = empty($v['attributes']['extra']) ? '' : $v['attributes']['extra'];
				}
				$fields[] = "`$fname` $ftype $fnull $fdefault $fextra";
				$fieldtypes[$fname] = $ftype;
			}
			if ($v['tag']=='key') {
				$fields[] = $v['value'];
			}
			if ($v['tag']='sqltable' && $v['type']=='close') {
				$sqldef .= ' ( '.implode(', ', $fields).' ) ';
				$this->definitionqueries[$tablename] = "$sqldef;";
				$this->fieldtypes[$tablename] = $fieldtypes;
			}
		}
	}

	function getFieldTypes() {
		return $this->fieldtypes;
	}

	function getFieldValues() {
		return $this->fieldvalues;
	}

	function getSQLDefinitionQueries() {
		return $this->definitionqueries;
	}

	function getSQLDataQueries() {
		return $this->insertqueries;
	}

}

class XMLCalibrationImport extends XMLImport {

	function XMLCalibrationImport($xmldata) {
		$this->importXML($xmldata);
		$this->XMLDefinition2SQL();
		$this->XMLData2SQL();
	}

	function XMLData2SQL() {
		$data = $this->data;
		foreach ($data as $d) {
			if ($d['tag']=='sqltable' && $d['type']='open') {
				$tablename = $d['attributes']['name'];
				$sqlinsert = "INSERT INTO $tablename  ";
				$fields = array();
				$values = array();
			}
			if ($d['tag']=='field') {
				$fname = $d['attributes']['name'];
				$addfield = true;
				switch($fname) {
				//--- Don't include the default primary Key Field into
				//--- the new query
				case "DEF_id": 
					$addfield = false;
				break;
				//--- Regenerate a new timestamp
				case "DEF_timestamp": 
					$fvalue = "NOW()";
				break;
				//--- Update the reference Id with $sessionId
				case "REF|SessionData|session": 
					$fvalue = '$sessionId';
				break;
				//--- Update the reference Id with $scopeId
				case "REF|InstrumentData|tem": 
					$fvalue = '$scopeId';
				break;
				//--- Update the reference Id with $cameraId
				case "REF|InstrumentData|ccdcamera": 
					$fvalue = '$cameraId';
				break;
				default:
					$fvalue = '"'.$d[value].'"';
				break;
				}
				if ($addfield) {
					$fields[] = '`'.$fname.'`';
					$values[] = $fvalue;
				}
			}
			if ($d['tag']=='sqltable' && $d['type']=='close') {
					$sqlinsert .= ' ('.implode(', ', $fields).') ';
					$sqlinsert .= ' VALUES ('.implode(', ', $values).') ';
					$this->insertqueries[$tablename][] = "$sqlinsert;";
			}
		}
	}
}

class XMLApplicationImport extends XMLImport {

	function XMLApplicationImport($xmldata) {
		$this->importXML($xmldata);
		$this->XMLDefinition2SQL();
		$this->XMLData2SQL();
	}

	function XMLData2SQL() {
		$data = $this->data;
		foreach ((array)$data as $d) {
			if ($d['tag']=='sqltable' && $d['type']=="open") {
				$tablename = $d['attributes']['name'];
				$sqlinsert = "INSERT INTO $tablename  ";
				$fields = array();
				$values = array();
				$fieldvalues= array();
			}
			if ($d['tag']=='field') {
				$fname = $d['attributes']['name'];
				$addfield = true;
				switch($fname) {
				//--- Don't include the default primary Key Field into
				//--- the new query
				case "DEF_id": 
					$addfield = false;
				break;
				//--- Regenerate a new timestamp
				case "DEF_timestamp": 
					$fvalue = "NOW()";
				break;
				//--- Update the reference Id with $applicationId
				case "REF|ApplicationData|application": 
					$fvalue = '$applicationId';
				break;
				default:
					$fvalue = '"'.$d['value'].'"';
				break;
				}
				if ($addfield) {
					$fieldvalues[$fname] = $fvalue;
					$fields[] = '`'.$fname.'`';
					$values[] = $fvalue;
				}
			}
			if ($d['tag']=='sqltable' && $d['type']=='close') {
				$sqlinsert .= ' ('.implode(', ', $fields).') ';
				$sqlinsert .= ' VALUES ('.implode(', ', $values).') ';
				$this->insertqueries[$tablename][] = "$sqlinsert;";
				$this->fieldvalues[$tablename] = $fieldvalues;
			}
		}
	}
}
?>
