<?php
require_once "inc/leginon.inc";
require_once "inc/image.inc";
require_once "inc/project.inc";
require_once "inc/particledata.inc";
require_once "inc/ace.inc";

$imgid=$_GET['id'];
$runid=$_GET['r'];
$preset=$_GET['preset'];
$imgsize=$_GET['s'];
$graphsc_x=$_GET['scx'];
$graphsc_y=$_GET['scy'];
if (!is_numeric($graphsc_x)) $graphsc_x=1;
if (!is_numeric($graphsc_y)) $graphsc_y=1;

// check the graph
switch($_GET['g']){
	case 2: $graph="graph2"; break;
	case 3: $graph="graph3"; break;
	case 4: $graph="graph4"; break;
	case 5: $graph="localplot"; break;
	default: $graph="graph1"; break;
}

// check the method
switch($_GET['m']){
	case 2: $ctfmethod="ace1"; break;
	case 3: $ctfmethod="ace2"; break;
	case 4: $ctfmethod="ctffind"; break;
	default: $ctfmethod=""; break;
}

$newimage = $leginondata->findImage($imgid, $preset);
$imgid = $newimage['id'];
$ctf = new particledata();
list($ctfdata) = $ctf->getCtfInfoFromImageId($imgid, $order=False, $ctfmethod, $runid);
$aceparams = $ctf->getAceParams($ctfdata['acerunId']);

// get the filename -- too many conventions...
// package 2D graph may have been moved to graph 1 when there is no appion fitting successful.
$basename = $ctfdata[$graph];
if ($_GET['g'] == 3 && !$basename) $basename = $ctfdata["graph1"];

if (!$basename) {
	header('Content-type: image/png');
	$blkimg = blankimage(256, 64, "CTF $graph not created");
	imagepng($blkimg);
	imagedestroy($blkimg);
	exit(1);
}

function is_redux_error($img) {
    return strpos($img, 'REDUX ERROR') === 0;
}

function echo_image($img) {
	header("Content-Type: image/png");
	header("Content-Length: " . strlen($img));
	echo($img);
}

$opfile = $ctfdata['path'].'/opimages/'.$basename;
$rtfile = $ctfdata['path'].'/'.$basename;

$img_requester = new imageRequester();
foreach (array($rtfile, $opfile) as $path) {
    $img = $img_requester->requestImage($path, 'PNG', $shape=false, $scaleType=false);
    if (!is_redux_error($img)) {
		echo_image($img);
		exit;
    }
}

error_log($img);

header('Content-type: image/png');
$blkimg = blankimage(256, 64, "CTF $graph file not found");
imagepng($blkimg);
imagedestroy($blkimg);

exit(1);

// .......................... not reached ..............................

if (file_exists($rtfile))
	$filename=$rtfile;
elseif (file_exists($opfile))
	$filename=$opfile;
else {
	header('Content-type: '.$imagemime);
	$blkimg = blankimage(256, 64, "CTF $graph file not found");
	imagepng($blkimg);
	imagedestroy($blkimg);
	exit(1);
}

// display the file
(array)$ctfimageinfo = @getimagesize($filename);
$imagecreate = 'imagecreatefrompng';
$imagemime = 'image/png';
switch ($ctfimageinfo['mime']) {
	case 'image/jpeg':
		$imagecreate = "imagecreatefromjpeg";
		$imagemime = $ctfimageinfo['mime'];
	break;
}

if ($img=@$imagecreate($filename)) {
	resample($img, $imgsize);
} else {
	header('Content-type: '.$imagemime);
	$blkimg = blankimage(256, 64, "CTF $graph file not found");
	imagepng($blkimg);
	imagedestroy($blkimg);
}

function rescaleArray($vals,$scx,$scy) {
	// need to add a selection for scaling
	$maxval = max($vals)*$scy;
	$vlen = count($vals)*$scx;
	$newvals=array();

	$valcount = 0;
	foreach ($vals as $val) {
		if ($val > $maxval) $newvals[]=$maxval;
		elseif (-$val > $maxval) $newvals[]=-$maxval;
		else $newvals[]=$val;
		$valcount++;
		if ($valcount > $vlen) break;
	}
	return $newvals;
}
?>
