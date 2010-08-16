<?php
require "inc/leginon.inc";
require "inc/viewer.inc";
require "inc/project.inc";
require "inc/cachedb.inc";
if (defined('PROCESSING')) {
	$ptcl = (require_once "inc/particledata.inc") ? true : false;
}

$sessionId = ($_POST['sessionId']) ? $_POST['sessionId'] : $_GET['expId'];
$projectId = ($_POST['projectId']) ? $_POST['projectId'] : $_GET['projectId'];
$imageId = ($_POST['imageId']) ? $_POST['imageId'] : $_GET['imageId'];
$preset = $_POST[$_POST['controlpre']];

// --- Set sessionId
$lastId = $leginondata->getLastSessionId();
$sessionId = (empty($sessionId)) ? $lastId : $sessionId;

$sessioninfo=$leginondata->getSessionInfo($sessionId);
$session=$sessioninfo['Name'];
startcache($session);

$projectdata = new project();
$projectdb = $projectdata->checkDBConnection();

if(!$sessions) {
	$sessions = $leginondata->getSessions('description', $projectId);
}

if($projectdb) {
	$projects = $projectdata->getProjects('all');
	$sessionexists = $projectdata->sessionExists($projectId, $sessionId);
	if (!$sessionexists) {
		$sessionId = $sessions[0]['id'];
	}
}

if ($ptcl) {
	$particle = new particledata();
	$particleruns=$particle->getParticleRunIds($sessionId);
}

// --- update SessionId while a project is selected
$sessionId_exists = $leginondata->sessionIdExists($sessions, $sessionId);
if (!$sessionId_exists) {
	$sessionId=$sessions[0]['id'];
}

$filenames = $leginondata->getFilenames($sessionId, $preset);

// --- Get data type list
$datatypes = $leginondata->getAllDatatypes($sessionId);

$viewer = new viewer();
if($projectdb) {
	foreach($sessions as $k=>$s) {
		if (SAMPLE_TRACK) {
			$tag=$projectdata->getSample(array('Id'=>$s['id'], 'Purpose'=>$s['comment']));
			$tag = ($tag)? " - $tag" : "";
			$sessions[$k]['name'].=$tag;
		}
		if ($s['id']==$sessionId) {
			$sessionname = $s['name_org'];
			// if name need to be modified by sample tag, it should not break
			// breaking is only to save query time
			if (!SAMPLE_TRACK)
				break;
		}
	}
	$currentproject = $projectdata->getProjectFromSession($sessionname);

	$viewer->setProjectId($projectId);
	$viewer->addProjectSelector($projects, $currentproject);
}
$viewer->setSessionId($sessionId);
$viewer->setImageId($imageId);
$viewer->addSessionSelector($sessions);
$viewer->addFileSelector($filenames);
$viewer->setNbViewPerRow('1');
$pl_refresh_time=".5";
$viewer->addPlaybackControl($pl_refresh_time);
$playbackcontrol=$viewer->getPlaybackControl();
$javascript = $viewer->getJavascript();

$view1 = new view('Main View', 'v1');
$view1->setControl();
$view1->setParam('ptclparams',$particleruns);
$view1->displayParticleIcon(false); 
$view1->displayComment(true); 
$view1->addMenuItems($playbackcontrol);
$view1->setDataTypes($datatypes);
$view1->displayPTCL(false);
$view1->setSize(512);
$viewer->add($view1);


$javascript .= $viewer->getJavascriptInit();
login_header('image viewer', $javascript, 'initviewer()');
viewer_menu($sessionId);
$viewer->display();
login_footer();
?>
