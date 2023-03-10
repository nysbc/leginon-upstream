<?php
require_once 'inc/leginon.inc';
require_once "inc/imagerequest.inc";
require_once "inc/image.inc";
$id=$_GET['id'];
$preset=$_GET['pr'];
$newimage = $leginondata->findImage($id, $preset);
$id=$newimage['id'];
$lj=boolval($_GET['lj']);
$filename=$leginondata->getFilenameFromId($id, true);
$filename=getImageFile($leginondata,$id,$preset,$lj,$is_fft=false,$cacheonly=false);
$imagerequest = new imageRequester();
$imginfo = $imagerequest->requestInfo($filename);
$min = $imginfo->amin;
$max = $imginfo->amax;
$mean = $imginfo->amean;
$stdev = $imginfo->rms;

function formatnumber($number) {
	$number=number_format($number,1,'.','');
	return $number;
}
$min=formatnumber($min);
$max=formatnumber($max);
$mean=formatnumber($mean);
$stdev=formatnumber($stdev);

header('Content-Type: text/xml');
echo '<?xml version="1.0" standalone="yes"?>';
echo "<data>";
echo "<min>";
echo $min;
echo "</min>";
echo "<max>";
echo $max;
echo "</max>";
echo "<mean>";
echo $mean;
echo "</mean>";
echo "<stdev>";
echo $stdev;
echo "</stdev>";
echo "</data>";
