
export function show(className : string, text : string, interval: number | null) : void {
	var id = "loadingWidget_" + className;
	if (document.getElementById(id) == null)
		document.body.insertAdjacentHTML("afterbegin", '<div id="'+id+'" class="messageBar"></div>');
	var el = document.getElementById(id)!!;
	el.innerText = text;
	el.classList.add(className);
	el.classList.add("visible");
	if (interval) setInterval(function() { hide(className); }, interval);
};
export function hide(className : string) {
	document.getElementById("loadingWidget_"+className)!!.classList.remove("visible");
};

document.body.insertAdjacentHTML("afterbegin", '<div class="progressBar" id="statusindicator_progressBar"></div>');
var loading = document.getElementById("statusindicator_progressBar")!!;
var timeout : number | null = null;
var loadingCtr = 0;
export function showProgress() {
	loading.classList.add("visible");
	loadingCtr++;
}
export function hideProgress() {
	if (loadingCtr > 0) loadingCtr--;
	if (loadingCtr > 0) return;
	if(timeout)clearTimeout(timeout);
	timeout = setTimeout(function() {
		loading.classList.remove("visible");
	});
}
