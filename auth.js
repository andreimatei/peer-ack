'use strict';


// The Google auth singleton.
var auth2;

function toggleSignedIn() {
  var signedIn = false;
  if (auth2 != undefined) {
    signedIn = auth2.isSignedIn.get();
  }
  if (signedIn) {
    var googleUser = auth2.currentUser.get()
    var profile = googleUser.getBasicProfile();
    set_id_token_cookie(googleUser.getAuthResponse().id_token);
    document.getElementById("signed-out-menu-content").style.display = "none";
    document.getElementById("signed-in-menu-content").style.display = "block";
    document.getElementById("user-photo").src = auth2.currentUser.get().getBasicProfile().getImageUrl();
    document.getElementById("user-name").innerHTML = profile.getName();
  } else {
    set_id_token_cookie("");
    document.getElementById("signed-out-menu-content").style.display = "block";
    document.getElementById("signed-in-menu-content").style.display = "none";
  }

  if (typeof page_toggleSignedIn === "function") {
    page_toggleSignedIn(signedIn)
  }
}

function onSignIn(googleUser) {
  console.log("Succesfully signed-in");
  var profile = googleUser.getBasicProfile();
  console.log('ID: ' + profile.getId()); 
  console.log('Name: ' + profile.getName());
  console.log('Image URL: ' + profile.getImageUrl());
  console.log('Email: ' + profile.getEmail());
  toggleSignedIn();
}

function onFailure(error) {
  console.log("failed to login: " + error);
  toggleSignedIn();
}

function signOut() {
    auth2.signOut().then(function () {
      console.log('User signed out.');
      toggleSignedIn();
    });
}

function initAuth() {
    gapi.load('auth2', function(){
      gapi.auth2.init({
          client_id: '431881615412-675868jddpuivt4di8pmqnm7k2bqm2jl.apps.googleusercontent.com',
          cookiepolicy: 'single_host_origin',
          hosted_domain: 'cockroachlabs.com',
          // Request scopes in addition to 'profile' and 'email'
          //scope: 'additional_scope'
      }).then(function(auth){
        auth2 = auth;
        if (!auth.isSignedIn.get()) {
          signOut();
        }
      });
    });
    gapi.signin2.render('signin-btn', {
        'scope': 'profile email',
        'onsuccess': onSignIn,
        'onfailure': onFailure,
    });
}

function set_id_token_cookie(id_token) {
  if (id_token == "") {
    // Clear the cookie.
    console.log("Clearing signed-in cookie");
    document.cookie = "id-token=;expires=Thu, 01 Jan 1970 00:00:01 GMT;";
    return;
  }
  document.cookie = `id-token=${id_token}; expires=Fri, 31 Dec 9999 23:59:59 GMT`;
}

function get_id_token_cookie() {
  return document.cookie.replace(
    /(?:(?:^|.*;\s*)id-token\s*\=\s*([^;]*).*$)|^.*$/, "$1");
}
