import { NextRequest, NextResponse } from 'next/server';
import { exec } from 'child_process';
import util from 'util';
import path from 'path';
import fs from 'fs';

const execPromise = util.promisify(exec);

export async function POST(req: NextRequest) {
  try {
    // Run the Python support agent demo in recording mode
    const command = 'PYTHONPATH=. python3 examples/run_demo.py';
    const { stdout } = await execPromise(command, { cwd: process.cwd() });
    
    // Copy the fresh demo_trace.jsonl to traces/customer-support.jsonl
    const demoTracePath = path.join(process.cwd(), 'demo_trace.jsonl');
    const destTracePath = path.join(process.cwd(), 'traces', 'customer-support.jsonl');
    
    if (fs.existsSync(demoTracePath)) {
      // Overwrite customer-support trace with fresh run logs
      fs.copyFileSync(demoTracePath, destTracePath);
      return NextResponse.json({
        status: 'success',
        message: 'Successfully triggered live agent recording and updated customer-support.jsonl.',
        consoleOutput: stdout,
      });
    }

    return NextResponse.json({
      status: 'error',
      message: 'Demo execution finished but trace file was not generated.',
      consoleOutput: stdout,
    });

  } catch (error: any) {
    console.error('Recording error:', error);
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}
