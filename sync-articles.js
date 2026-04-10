const { createClient } = require('@supabase/supabase-js');
const fs = require('fs');
const path = require('path');

// Initialize Supabase Client
const supabaseUrl = 'https://pddrwxvauofsnchcmodn.supabase.co';
const supabaseKey = 'sb_publishable_w_x9uuDPvOxYBpEr8Q4k6Q_ZHNAbMuX';
const supabaseClient = createClient(supabaseUrl, supabaseKey);

async function syncPosts() {
    console.log('🔄 Fetching published posts from Supabase...');
    
    const { data: posts, error } = await supabaseClient
        .from('posts')
        .select('*')
        .eq('status', 'published')
        .order('published_at', { ascending: false });

    if (error) {
        console.error('❌ Error fetching posts from Supabase:', error.message);
        process.exit(1);
    }

    console.log(`✅ Successfully fetched ${posts.length} posts.`);

    const outputPath = path.join(__dirname, 'posts.json');
    
    try {
        fs.writeFileSync(outputPath, JSON.stringify(posts, null, 2));
        console.log(`💾 Saved directly to static file: ${outputPath}`);
    } catch (writeError) {
        console.error('❌ Error writing to json file:', writeError);
    }
}

syncPosts();
