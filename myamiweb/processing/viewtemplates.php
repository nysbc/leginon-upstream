<?php
/**
 *	The Leginon software is Copyright 2003 
 *	The Scripps Research Institute, La Jolla, CA
 *	For terms of the license agreement
 *	see  http://ami.scripps.edu/software/leginon-license
 *
 *	Simple viewer to view a image using mrcmodule
 */

require "inc/particledata.inc";
require "inc/leginon.inc";
require "inc/project.inc";
require "inc/processing.inc";

$expId = (int) $_GET['expId'];
$formAction=$_SERVER['PHP_SELF']."?expId=$expId";
if ($_GET['showHidden']) $formAction.="&showHidden=True";

$javascript = editTextJava();

processing_header("Template Summary", "Template Summary", $javascript,False);

if ($expId && is_int($expId)){
	$projectId = (int) getProjectFromExpId($expId);
}

if (is_int($projectId)) {
	$particle=new particleData;
	$templateData=$particle->getTemplatesFromProject($projectId,True);
}


// edit description form
echo "<form name='templateform' method='post' action='$formAction'>\n";

// extract template info
if ($templateData) {
	// separate hidden from shown;
	$shown = array();
	$hidden = array();
	foreach($templateData as $templateinfo) { 
		if (is_array($templateinfo)) {
			$templateId=$templateinfo['DEF_id'];
			// first update hide value
			if ($_POST['hideTemplate'.$templateId]) {
				$particle->updateHide('ApTemplateImageData',$templateId,1);
				$templateinfo['hidden']=1;
			}
			elseif ($_POST['unhideTemplate'.$templateId]) {
				$particle->updateHide('ApTemplateImageData',$templateId,0);
				$templateinfo['hidden']='';
			}
			if ($templateinfo['hidden']==1) $hidden[]=$templateinfo;
			else $shown[]=$templateinfo;
		}
	}
	$templatetable='';
	foreach ($shown as $templateinfo) $templatetable.=templateEntry($templateinfo);
	// show hidden templates
	if ($_GET['showHidden'] && $hidden) {
		$templatetable.="<b>Hidden Templates</b> ";
		$templatetable.="<a href='".$_SERVER['PHP_SELF']."?expId=$expId'>[hide]</a><br />\n";
		foreach ($hidden as $templateinfo) $templatetable.= templateEntry($templateinfo,True);
	}
	$templatetable.="</form>\n";
}

if ($hidden && !$_GET['showHidden']) echo "<a href='".$formAction."&showHidden=True'>Show Hidden Templates</a><br />\n";

if ($shown || $hidden) echo $templatetable;
else echo "<B>Project does not contain any templates.</B>\n";
processing_footer();
exit;

function templateEntry($templateinfo, $hidden=False){
	$templateId=$templateinfo['DEF_id'];
	if ($_POST['updateDesc'.$templateId]) {
		updateDescription('ApTemplateImageData', $templateId, $_POST['newdescription'.$templateId]);
		$templateinfo['description']=$_POST['newdescription'.$templateId];
	}
	$filename = $templateinfo['path'] ."/".$templateinfo['templatename'];
	// create the image template table
	$j = "Template ID: $templateId";
	if ($hidden) $j.= " <input class='edit' type='submit' name='unhideTemplate".$templateId."' value='unhide'>";
	else $j.= " <input class='edit' type='submit' name='hideTemplate".$templateId."' value='hide'>";
	$templatetable.= apdivtitle($j);
	$templatetable.="<table border='0' cellpadding='5'>\n";
	$templatetable.="<tr><td valign='top'>\n";
	$templatetable.="<img src='loadimg.php?filename=$filename&rescale=True' width='100'></td>\n";
	$templatetable.="<td>\n";
	$templatetable.="<B>Diameter:</B>  $templateinfo[diam]<BR/>\n";
	$templatetable.="<B>Pixel Size:</B>  $templateinfo[apix]<BR/>\n";
	$templatetable.="<B>File:</B><BR/>";
	$templatetable.=$filename;
	$templatetable.="<br />\n";
	$templatetable.="<b>Description:</b><br />";

	# add edit button to description if logged in
	$descDiv = ($_SESSION['username']) ? editButton($templateId,$templateinfo['description']) : $templateinfo['description'];
	$templatetable.=$descDiv;
	$templatetable.="</td></tr>\n";
	$templatetable.="</table>\n";
	return $templatetable;
}
?>
