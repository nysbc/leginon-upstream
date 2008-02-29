<?php
/**
 *	The Leginon software is Copyright 2003 
 *	The Scripps Research Institute, La Jolla, CA
 *	For terms of the license agreement
 *	see  http://ami.scripps.edu/software/leginon-license
 *
 *	Display results for each iteration of a refinement
 */

require "inc/particledata.inc";
require "inc/leginon.inc";
require "inc/project.inc";
require "inc/viewer.inc";
require "inc/processing.inc";
  
// check if reconstruction is specified
if (!$reconId = $_GET['reconId'])
	$reconId=false;
$expId = $_GET['expId'];

$refine_params_fields = array('refinerun', 'ang', 'mask', 'imask', 'pad', 'hard', 'classkeep', 'classiter', 'median', 'phasecls', 'refine','cckeep','minptls');
$javascript="<script src='../js/viewer.js'></script>\n";

// javascript to display the refinement parameters
$javascript="<script LANGUAGE='JavaScript'>
        function infopopup(";
foreach ($refine_params_fields as $param) {
        if (ereg("\|", $param)) {
	        $namesplit=explode("|", $param);
		$param=end($namesplit);
	}
	$refinestring.="$param,";
}
$refinestring=rtrim($refinestring,',');
$javascript.=$refinestring;
$javascript.=") {
                var newwindow=window.open('','name','height=400, width=200, resizable=1, scrollbar=1');
                newwindow.document.write(\"<HTML><HEAD><link rel='stylesheet' type='text/css' href='css/viewer.css'>\");
                newwindow.document.write('<TITLE>Ace Parameters</TITLE>');
                newwindow.document.write(\"</HEAD><BODY><TABLE class='tableborder' border='1' cellspacing='1' cellpadding='5'>\");\n";
foreach($refine_params_fields as $param) {
        if (ereg("\|", $param)) {
	        $namesplit=explode("|", $param);
		$param=end($namesplit);
	}
	$javascript.="                if ($param) {\n";
	$javascript.="                        newwindow.document.write('<TR><TD>$param</TD>');\n";
        $javascript.="                        newwindow.document.write('<TD>'+$param+'</TD></TR>');\n";
        $javascript.="                }\n";
}
$javascript.="                newwindow.document.write('</TABLE></BODY></HTML>');\n";
$javascript.="                newwindow.document.close()\n";
$javascript.="        }\n";
$javascript.="</script>\n";
 
writeTop("Reconstruction Report","Reconstruction Report Page", $javascript);
if (!$reconId) {
	writeBottom();
	exit;
}

// --- Get Reconstruction Data
$particle = new particledata();
$stackId = $particle->getStackIdFromReconId($reconId);
$stackparticles = $particle->getNumStackParticles($stackId);
$stackparams = $particle->getStackParams($stackId);
// get pixel size
$apix=($particle->getStackPixelSizeFromStackId($stackId))*1e10;
// don't think we need to calculate the binned pixel size
//$apix=($stackparams['bin']) ? $apix*$stackparams['bin'] : $apix;
$boxsz=($stackparams['bin']) ? $stackparams['boxSize']/$stackparams['bin'] : $stackparams['boxSize'];

$html = "<BR>\n<table class='tableborder' border='1' cellspacing='1' cellpadding='5'>\n";
$html .= "<TR>\n";
$display_keys = array ( 'iter', 'ang', 'res', 'fsc', 'classes', '# particles', 'density','snapshot');
foreach($display_keys as $key) {
        $html .= "<TD><span class='datafield0'>".$key."</span> </TD> ";
}
$html .= "</TR>\n";

$refinerun=$particle->getRefinementRunInfo($reconId);
$initmodel=$particle->getInitModelInfo($refinerun['REF|ApInitialModelData|initialModel']);

$stackfile=$stackparams['path']."/".$stackparams['name'];
$initmodelname=$initmodel['name'];
$symdata=$particle->getSymInfo($initmodel['REF|ApSymmetryData|symmetry']);
$res = $particle->getHighestResForRecon($refinerun['DEF_id']);
$avgmedjump = $particle->getAverageMedianJump($refinerun['DEF_id']);
if ($avgmedjump['count'] > 0) {
	$avgmedjumpstr .= "<A HREF='eulergraph.php?hg=1&recon=$refinerun[DEF_id]'>";
	$avgmedjumpstr .= sprintf("%2.2f &plusmn; %2.1f </A>", $avgmedjump['average'], $avgmedjump['stdev']);
} else
	$avgmedjumpstr = NULL;


$title = "recon info";
//print_r($refinerun);


$reconinfo = array(
	'id'=>"<A TARGET='reconsummary' HREF='reconsummary.php?expId=$expId'>$refinerun[DEF_id]</A>",
	'name'=>$refinerun['name'],
	'description'=>$refinerun['description'],
	'path'=>$refinerun['path'],
	'symmetry'=>$refinerun['symmetry'],
	'refine package'=>$refinerun['package'],
	'best resolution'=>	sprintf("% 2.2f / % 2.2f &Aring; (%d)", $res[half],$res[rmeas],$res[iter]),
	'median euler jump'=>$avgmedjumpstr,
);
$particle->displayParameters($title,$reconinfo,array());


$title = "stack info";
$apixstr=format_angstrom_number($apix/1e10)."/pixel";
//print_r($stackparams);
$stackinfo = array(
	'id'=>"<A TARGET='stackreport' HREF='stackreport.php?expId=$expId&sId=$stackId'>$stackId</A>",
	'runid'=>$stackparams[0]['stackRunName'],
	'description'=>$stackparams['description'],
	'name'=>"<A TARGET='stackview' HREF='viewstack.php?expId=$expId&stackId=$stackId&file=$stackfile'>$stackparams[name]</A>",
	'path'=>$stackparams['path'],
	'num part'=>commafy($stackparticles),
	'pixel/box size'=>$apixstr."; ".$stackparams['boxSize']." pixels"
);
$particle->displayParameters($title,$stackinfo,array());

$title = "model info";
//print_r($initmodel);
$modelinfo = array(
	'id'=>"<A TARGET='viewmodels' HREF='viewmodels.php?expId=$expId'>$initmodel[DEF_id]</A>",
	'description'=>$initmodel['description'],
	'path'=>$initmodel['path']."/".$initmodelname,
	'symmetry'=>$symdata['symmetry'].", ".$symdata['description'],
	'pixel/box size'=>format_angstrom_number($initmodel['pixelsize']/1e10)."/pixel; ".$initmodel['boxsize']." pixels",
);
$particle->displayParameters($title,$modelinfo,array());

$misc = $particle->getMiscInfoFromReconId($reconId);
if ($misc) echo "<A HREF='viewmisc.php?reconId=$reconId'>[Related Images, Movies, etc]</A><BR>\n"; 

$iterations = $particle->getIterationInfo($reconId);

# get starting model png files
$initpngs = array();
$initdir = opendir($initmodel['path']);
while ($f = readdir($initdir)){
  if (eregi($initmodelname.'.*\.png$',$f)) {
    $initpngs[] = $f;
  }
}
sort($initpngs);

# get list of png files in directory
$pngfiles=array();
$refinedir = opendir($refinerun['path']);
while ($f = readdir($refinedir)) {
  if (eregi('\.png$',$f)) {
    $pngfiles[] = $f;
  }
}
sort($pngfiles);

# display starting model
$html .= "<TR>\n";
foreach ($display_keys as $p) {
  $html .= "<TD>";
  if ($p == 'iteration') $html .= "0";
  elseif ($p == 'snapshot') {
    foreach ($initpngs as $snapshot) {
      $snapfile = $initmodel['path'].'/'.$snapshot;
      $html .= "<A HREF='loadimg.php?filename=$snapfile' target='snapshot'><IMG SRC='loadimg.php?filename=$snapfile' HEIGHT='80'>\n";
    }
  }
  $html .= "</TD>";
}
$html .= "</TR>\n";

# show info for each iteration
//sort($iterations);
foreach ($iterations as $iteration){
  $refinementData=$particle->getRefinementData($refinerun['DEF_id'], $iteration['iteration']);
  $numclasses=$particle->getNumClasses($refinementData['DEF_id']);
  $res = $particle->getResolutionInfo($iteration['REF|ApResolutionData|resolution']);
  $RMeasure = $particle->getRMeasureInfo($iteration['REF|ApRMeasureData|rMeasure']);
  $fscfile = ($res) ? $refinerun['path'].'/'.$res['fscfile'] : "None" ;
  $halfres = ($res) ? sprintf("%.2f",$res['half']) : "None" ;
  $rmeasureres = ($RMeasure) ? sprintf("%.2f",$RMeasure['rMeasure']) : "None" ;
  $badprtls=$particle->getNumBadParticles($refinementData['DEF_id']);
  $msgpbadprtls=$particle->getNumMsgPRejectParticles($refinementData['DEF_id']);
  $prtlsused=$stackparticles-$badprtls;
  $goodprtlsused=$stackparticles-$msgpbadprtls;
  $html .= "<TR>\n";
  $html .= "<TD><A HREF=\"javascript:infopopup(";
  $refinestr2='';
  foreach ($refine_params_fields as $param) {
    if (eregi('hard|class|median|phasecls|refine',$param)){$param="EMAN_$param";}
    if (eregi('cckeep|minptls',$param)){$param="MsgP_$param";}
		$refinestr2.="'$iteration[$param]',";
  }
  $refinestr2=rtrim($refinestr2,',');
  $html .=$refinestr2;
  $html .=")\">$iteration[iteration]</A></TD>\n";
  $html .= "<TD>$iteration[ang]&deg;</TD>\n";
  $html .= "<TD><I>FSC 0.5:</I><br />$halfres<br />\n";
  
  if ($rmeasureres!='None')
    $html .= "<I>Rmeas:</I><br>$rmeasureres\n";
  $html .= "</TD>";
  
  if ($halfres!='None')
    $html .= "<TD><A HREF='fscplot.php?fscfile=$fscfile&width=800&height=600&apix=$apix&box=$boxsz'><IMG SRC='fscplot.php?fscfile=$fscfile&width=100&height=80&nomargin=TRUE'>\n";
  else $html .= "<TD>-</TD>\n";
  $html .="<TD><table>";
  $clsavg = $refinerun['path'].'/'.$iteration['classAverage'];
	$html .= "<TR><TD>";
	$html .= "$numclasses classes<br />\n";
	$html .= "<a target='stackview' href='viewstack.php?file=$clsavg'>".$iteration['classAverage']."</a><br />";
	// Euler Plots
	$oldeulerfile = $refinerun['path']."/eulermap".$iteration['iteration'].".png";
	if (file_exists($oldeulerfile)) {
		$html .= "<a target='eulermap' href='loadimg.php?filename=".$oldeulerfile."'>"
		."<img src='loadimg.php?scale=.125&filename=".$oldeulerfile."'>"
		."</a>";
	}
	$eulertrifile = $refinerun['path']."/eulerTriangle-".$refinerun['DEF_id']."_".$iteration['iteration'].".png";
	if (file_exists($eulertrifile)) {
		$html .= "<a target='eulertriangle' href='loadimg.php?filename=".$eulertrifile."'>"
		."<img src='loadimg.php?scale=.125&filename=".$eulertrifile."'>"
		."</a>";
	}
	$eulerpolarfile = $refinerun['path']."/eulerPolar-".$refinerun['DEF_id']."_".$iteration['iteration'].".png";
	if (file_exists($eulerpolarfile)) {
		$html .= "<a target='eulerpolar' href='loadimg.php?filename=".$eulerpolarfile."'>"
		."<img src='loadimg.php?scale=.125&filename=".$eulerpolarfile."'>"
		."</a>";
	}

	$html .= "</td></tr>\n";
  
  if ($refinerun['package']=='EMAN/MsgP') {
    $goodavg = $refinerun['path'].'/'.$iteration['MsgPGoodClassAvg'];
    $html .= "<TR><TD><A TARGET='stackview' HREF='viewstack.php?uh=1&file=$goodavg'>$iteration[MsgPGoodClassAvg]</A></TD></TR>\n";
  }
  $html .= "</table></TD>";
  
  
  $html .="<TD><table>";
  $html .= "<TR><TD ALIGN='CENTER'>"
		."<A TARGET='stackview' HREF='viewstack.php?refinement=$refinementData[DEF_id]&substack=good'>[$prtlsused good]</A><BR/>"
		."<A TARGET='stackview' HREF='viewstack.php?refinement=$refinementData[DEF_id]&substack=bad'>[$badprtls bad]</A>"
		."</TD></TR>\n";
  if ($refinerun['package']=='EMAN/MsgP') 
    $html .= "<TR><TD>$goodprtlsused MsgP<BR><A TARGET='stackview' HREF='viewstack.php?refinement=$refinementData[DEF_id]&substack=msgpbad'>[$msgpbadprtls bad]</A></TD></TR>\n";
  $html .= "</table></TD>";
  
  $html .= "</TD>\n";
  $html .= "<td>$iteration[volumeDensity]<br />\n";
  $html .= "<A HREF='postproc.php?expId=$expId&refinement=$refinementData[DEF_id]'><FONT CLASS='sf'>[post processing]</FONT></a><br />\n";
  $html .= "<A HREF='makegoodavg.php?expId=$expId&refId=$refinementData[DEF_id]&reconId=$reconId&iter=$iteration[iteration]'><FONT CLASS='sf'>[new averages]</FONT></a>\n";
  $html .= "</td>\n";
  $html .= "<td>\n";
  foreach ($pngfiles as $snapshot) {
    if (eregi($iteration['volumeDensity'],$snapshot)) {
      $snapfile = $refinerun['path'].'/'.$snapshot;
      $html .= "<A HREF='loadimg.php?filename=$snapfile' target='snapshot'><IMG SRC='loadimg.php?filename=$snapfile' HEIGHT='80'>\n";
    }
	}
  $html .= "</TD>\n";
  $html .= "</TR>\n";
}
$html.="</TABLE>\n";

echo "<P><FORM NAME='compareparticles' METHOD='POST' ACTION='compare_eulers.php'>
Compare Iterations:
<select name='comp_param'>\n";
echo "<option>Eulers</option>\n";
echo "<option>Inplane rotation</option>\n";
echo "<option>Shifts</option>\n";
echo "<option>Quality Factor</option>\n";
echo "</select>\n";
echo "Iteration 1: <select name='iter1'>\n";
foreach ($iterations as $iteration){
        echo "<option>$iteration[iteration]</option>\n";
}
echo "</select>\n";
echo "Iteration 2: <select name='iter2'>\n";
foreach ($iterations as $iteration){
        echo "<option>$iteration[iteration]</option>\n";
}
echo "</select>\n";
echo "<br />";
echo "download: <input type='checkbox' name='dwd' >\n";
echo "<input type='submit' name='compare' value='compare'>\n";
echo "<input type='hidden' name='reconId' value='$reconId'>\n";
echo "</FORM>\n";

$comm_param = ($_POST[comm_param]) ? $_POST[comm_param] : 'bad';
$iter1 = ($_POST[iter1]) ? $_POST[iter1] : $iterations[0][iteration];
$iter2 = ($_POST[iter2]) ? $_POST[iter2] : $iterations[0][iteration];
$formaction =  'viewstack.php?recon='.$reconId.'&substack='.$comm_param.'&itr1='.$iter1.'&itr2='.$iter2;
echo "<P><FORM NAME='commonparticles' target='stackview' METHOD='POST' ACTION=$formaction>
Show Common Particles Between Iterations:";
echo "
	<select name='comm_param'>\n";
$comm_params = array('bad'=>'Bad by EMAN refine',
	'good'=>'Good by EMAN refine');
if ($refinerun['package']=='EMAN/MsgP') { 
		$comm_params_msgp = array('msgpbad'=>'Bad by Msg Passing');
		$comm_params = array_merge($comm_params,$comm_params_msgp);
}
foreach (array_keys($comm_params) as $key) {
	$s = ($comm_param==$key) ? 'selected' : '';
	echo "<option value=$key $s>$comm_params[$key]</option>\n";
}
echo "</select>\n";
echo "From Iteration: <select name='iter1'>\n";
foreach ($iterations as $iteration){
	$s = ($iter1==$iteration[iteration]) ? 'selected' : '';
	echo "<option $s>$iteration[iteration]</option>\n";
}
echo "</select>\n";
echo "To: <select name='iter2'>\n";
foreach ($iterations as $iteration){
	$s = ($iter2==$iteration[iteration]) ? 'selected' : '';
	echo "<option $s>$iteration[iteration]</option>\n";
}
echo "</select>\n";
echo "<input type='submit' name='common particles' value='Show Common Particles' >\n";
echo "<br />";
echo "</FORM>\n";

echo $html;

writeBottom();
?>
