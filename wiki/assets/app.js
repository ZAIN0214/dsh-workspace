(function(){
  // 主题
  var root=document.documentElement, btn=document.getElementById('themeBtn');
  var saved=localStorage.getItem('wiki-theme');
  if(saved){root.setAttribute('data-theme',saved);}
  else if(window.matchMedia('(prefers-color-scheme:dark)').matches){root.setAttribute('data-theme','dark');}
  function paint(){
    btn.textContent = root.getAttribute('data-theme')==='dark' ? '☀️' : '🌙';
  }
  paint();
  btn.addEventListener('click',function(){
    var next = root.getAttribute('data-theme')==='dark' ? 'light' : 'dark';
    root.setAttribute('data-theme',next);
    localStorage.setItem('wiki-theme',next);
    paint();
  });

  // 移动端目录
  var menu=document.getElementById('menuBtn'), side=document.getElementById('sidebar');
  if(menu&&side){
    menu.addEventListener('click',function(){side.classList.toggle('open');});
    side.addEventListener('click',function(e){
      if(e.target.tagName==='A'){side.classList.remove('open');}
    });
  }

  // 搜索（仅首页）
  var input=document.getElementById('searchInput');
  if(!input) return;
  var box=document.getElementById('searchResults'), data=null, loading=false;

  function load(cb){
    if(data) return cb();
    if(loading) return;
    loading=true;
    fetch('assets/search-index.json').then(function(r){return r.json();}).then(function(d){
      data=d; cb();
    }).catch(function(){
      box.innerHTML='<div class="sr-empty">搜索索引加载失败（本地直接双击打开文件时会出现，用 http 访问即可）。</div>';
    });
  }

  function esc(s){
    return String(s).replace(/[&<>"]/g,function(c){
      return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c];
    });
  }

  function render(q){
    q=q.trim().toLowerCase();
    if(!q){box.innerHTML='';return;}
    var hits=data.filter(function(n){
      var hay=(n.t+' '+n.d+' '+n.c+' '+(n.k||[]).join(' ')).toLowerCase();
      return hay.indexOf(q)>=0;
    });
    if(!hits.length){box.innerHTML='<div class="sr-empty">没找到「'+esc(q)+'」相关的笔记。</div>';return;}
    box.innerHTML=hits.map(function(n){
      return '<a class="sr-item" href="'+n.u+'"><b>'+esc(n.t)+'</b>'+
        '<span><em>'+esc(n.c)+'</em>'+esc(n.d)+'</span></a>';
    }).join('');
  }

  var timer=null;
  input.addEventListener('input',function(){
    var q=input.value;
    clearTimeout(timer);
    timer=setTimeout(function(){
      load(function(){render(q);});
    },120);
  });

  // 从别的页面带 ?q= 过来时自动搜
  var params=new URLSearchParams(location.search);
  var q0=params.get('q');
  if(q0){input.value=q0;load(function(){render(q0);});}
})();
